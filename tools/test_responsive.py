#!/usr/bin/env python3
"""Tests de régression du responsive, mesurés dans un vrai navigateur.

    python3 tools/test_responsive.py    # sans rien installer, hors Chrome
    pytest tools/test_responsive.py     # si pytest est disponible

Origine : sur téléphone, le bouton « Naviguer » sortait de l'écran de
vingt-cinq pixels. Les règles mobiles de l'en-tête existaient pourtant. Ce qui
les rendait mortes ne se voit pas à la lecture : la règle de base s'écrit
« header.hud-top » (spécificité 0,1,1), le bloc mobile « .hud-top » (0,1,0),
et le premier l'emporte. Relire la feuille de style ne pouvait pas le dire ;
seule la mesure le pouvait.

D'où ces tests : ils ouvrent les pages dans Chrome sans interface, aux largeurs
des téléphones courants, et vérifient qu'aucun élément ne dépasse le bord de
l'écran. Un débordement toléré est un débordement à l'intérieur d'un conteneur
qui défile (« .tablewrap », « pre ») : c'est le comportement voulu pour un
tableau large, pas un défaut de mise en page.

Chrome absent : les tests sont ignorés plutôt qu'échoués, pour que le dépôt
reste utilisable sans lui. La CI, elle, l'a toujours.
"""
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from functools import lru_cache
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent

# Les pages livrées, celles qu'un visiteur peut ouvrir depuis un téléphone.
PAGES = ('index.html', 'rapport.html', 'carte-mentale.html')

# iPhone SE, Android courant, iPhone récent, Pixel. En dessous de 320 px il n'y
# a plus de téléphone à servir.
WIDTHS = (320, 360, 390, 412)

# Recommandation d'accessibilité pour une cible tactile ; on ne l'applique qu'à
# la barre fixe, seule zone où le doigt vise des icônes sans libellé.
MIN_TOUCH = 40


def chrome():
    """Le binaire Chrome, ou None : sans lui les tests s'ignorent."""
    for name in ('google-chrome', 'chromium', 'chromium-browser', 'google-chrome-stable'):
        found = shutil.which(name)
        if found:
            return found
    return None


class _Quiet(SimpleHTTPRequestHandler):
    """Sert le dépôt sans écrire une ligne par requête dans la sortie."""

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass


def _free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


# Les pages sont servies en HTTP et non ouvertes en file:// : la recherche
# vectorielle charge son index par fetch, que le protocole file:// refuse. Sous
# file:// la page se chargerait en apparence, sans son moteur de recherche.
@lru_cache(maxsize=1)
def _server():
    port = _free_port()
    httpd = ThreadingHTTPServer(('127.0.0.1', port), _Quiet)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{port}'


# Mesure faite dans la page. Un élément ne compte comme débordant que si aucun
# de ses parents ne défile ni ne rogne : sinon un tableau large, volontairement
# placé dans un conteneur à défilement, serait signalé à tort.
PROBE = """
(() => {
  document.querySelectorAll('.reveal').forEach(e => e.classList.add('in'));
  const vw = document.documentElement.clientWidth;
  const escapes = el => {
    let p = el.parentElement;
    while (p && p !== document.body) {
      const ox = getComputedStyle(p).overflowX;
      if (ox === 'auto' || ox === 'scroll' || ox === 'hidden') return false;
      p = p.parentElement;
    }
    return true;
  };
  const over = [];
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.right <= vw + 1) return;
    if (el.classList.contains('skip')) return;   // lien d'évitement, hors écran par construction
    if (!escapes(el)) return;
    over.push({
      tag: el.tagName,
      cls: (el.className || '').toString().slice(0, 40),
      right: Math.round(r.right),
      text: (el.textContent || '').trim().slice(0, 40)
    });
  });
  const touch = [];
  document.querySelectorAll('header.hud-top button').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && (r.width < %(min_touch)d || r.height < %(min_touch)d)) {
      touch.push({
        id: el.id,
        size: Math.round(r.width) + 'x' + Math.round(r.height)
      });
    }
  });
  return JSON.stringify({
    viewport: vw,
    scrollWidth: document.documentElement.scrollWidth,
    overflow: over.slice(0, 12),
    smallTargets: touch
  });
})()
"""


def _cdp_measure(page, width):
    """Mesure via le protocole de débogage : la seule voie qui rend une valeur."""
    binary = chrome()
    port = _free_port()
    # Chrome continue d'écrire dans son profil un instant après l'arrêt :
    # « ignore_cleanup_errors » évite que ce dernier soupir fasse échouer un
    # test qui, lui, a déjà rendu son verdict.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        proc = subprocess.Popen(
            [binary, '--headless=new', '--disable-gpu', '--no-sandbox',
             f'--user-data-dir={profile}', f'--remote-debugging-port={port}',
             f'--window-size={width},900', '--force-device-scale-factor=1',
             'about:blank'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            target = None
            for _ in range(80):
                try:
                    tabs = json.loads(urlopen(f'http://127.0.0.1:{port}/json/list',
                                              timeout=2).read())
                    target = next((t for t in tabs if t['type'] == 'page'), None)
                    if target:
                        break
                except Exception:
                    time.sleep(0.25)
            assert target, "Chrome n'a pas ouvert d'onglet de débogage"
            return _drive(target['webSocketDebuggerUrl'], page, width)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


def _ws_connect(ws_url):
    """Ouvre la connexion WebSocket à la main.

    Le protocole de débogage de Chrome ne parle que WebSocket, et la
    bibliothèque standard n'en fournit pas de client. Plutôt que d'imposer une
    dépendance pour trois messages échangés avec un navigateur local, on écrit
    la poignée de main et le cadrage : le strict nécessaire, sans masquage ni
    fragmentation, ce que Chrome accepte pour des messages de cette taille.
    """
    import base64
    import os
    from urllib.parse import urlparse

    u = urlparse(ws_url)
    sock = socket.create_connection((u.hostname, u.port), timeout=30)
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall((
        f"GET {u.path} HTTP/1.1\r\n"
        f"Host: {u.hostname}:{u.port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    ).encode())

    buf = b''
    while b'\r\n\r\n' not in buf:
        chunk = sock.recv(4096)
        assert chunk, "Chrome a fermé la connexion pendant la poignée de main"
        buf += chunk
    assert b'101' in buf.split(b'\r\n')[0], f"Chrome a refusé la connexion : {buf[:80]}"
    return sock, buf.split(b'\r\n\r\n', 1)[1]


def _ws_send(sock, payload):
    """Envoie une trame texte masquée, comme l'exige un client."""
    import os
    import struct

    data = payload.encode()
    mask = os.urandom(4)
    n = len(data)
    header = b'\x81'
    if n < 126:
        header += struct.pack('!B', 0x80 | n)
    elif n < (1 << 16):
        header += struct.pack('!BH', 0x80 | 126, n)
    else:
        header += struct.pack('!BQ', 0x80 | 127, n)
    sock.sendall(header + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


def _ws_recv(sock, rest):
    """Lit une trame texte complète et rend son contenu, plus le reliquat."""
    import struct

    def take(n):
        nonlocal rest
        while len(rest) < n:
            chunk = sock.recv(65536)
            assert chunk, "Chrome a fermé la connexion"
            rest += chunk
        out, rest = rest[:n], rest[n:]
        return out

    frames = []
    while True:
        b0, b1 = take(2)
        length = b1 & 0x7F
        if length == 126:
            length = struct.unpack('!H', take(2))[0]
        elif length == 127:
            length = struct.unpack('!Q', take(8))[0]
        frames.append(take(length))          # un serveur ne masque jamais
        if b0 & 0x80:                        # bit FIN : message complet
            break
    return b''.join(frames).decode(), rest


def _drive(ws_url, page, width):
    """Pilote l'onglet : émule le téléphone, charge la page, relève les mesures."""
    sock, rest = _ws_connect(ws_url)
    seq = [0]

    def call(method, params=None):
        nonlocal rest
        seq[0] += 1
        _ws_send(sock, json.dumps({'id': seq[0], 'method': method,
                                   'params': params or {}}))
        while True:
            raw, rest = _ws_recv(sock, rest)
            msg = json.loads(raw)
            if msg.get('id') == seq[0]:      # les événements passent leur tour
                return msg

    try:
        call('Page.enable')
        call('Emulation.setDeviceMetricsOverride',
             {'width': width, 'height': 900, 'deviceScaleFactor': 1, 'mobile': True})
        call('Emulation.setTouchEmulationEnabled', {'enabled': True, 'maxTouchPoints': 5})
        call('Page.navigate', {'url': f'{_server()}/{page}'})
        time.sleep(4)
        res = call('Runtime.evaluate',
                   {'expression': PROBE % {'min_touch': MIN_TOUCH},
                    'returnByValue': True})
        return json.loads(res['result']['result']['value'])
    finally:
        sock.close()


@lru_cache(maxsize=None)
def layout(page, width):
    return _cdp_measure(page, width)


class Skipped(Exception):
    """Le test n'a pas pu s'exécuter — à ne surtout pas confondre avec un succès."""


def _skip(reason):
    """Ignore le test, sous pytest comme sans lui.

    L'exception est indispensable : sans elle un test ignoré rendrait la main
    normalement et se compterait comme passé. Une CI verte dirait alors que le
    responsive est vérifié sur une machine où rien n'a été mesuré.
    """
    try:
        import pytest
        pytest.skip(reason)
    except ImportError:
        raise Skipped(reason)


def _deps_missing():
    """Seul Chrome est requis : le reste tient dans la bibliothèque standard."""
    if not chrome():
        return "Chrome est absent de cette machine"
    return None


def test_aucun_debordement_horizontal():
    """Aucune page ne défile latéralement : c'est le symptôme visible du bug."""
    missing = _deps_missing()
    if missing:
        _skip(missing)
    for page in PAGES:
        for width in WIDTHS:
            m = layout(page, width)
            assert m['scrollWidth'] <= m['viewport'] + 1, (
                f"{page} à {width} px : la page déborde de "
                f"{m['scrollWidth'] - m['viewport']} px vers la droite")


def test_aucun_element_hors_ecran():
    """Le débordement d'un seul élément, même sans défilement de la page.

    C'est ce qui se passait pour « Naviguer » : la page ne défilait pas
    latéralement, mais le bouton sortait bel et bien de l'écran.
    """
    missing = _deps_missing()
    if missing:
        _skip(missing)
    for page in PAGES:
        for width in WIDTHS:
            m = layout(page, width)
            assert not m['overflow'], (
                f"{page} à {width} px : {len(m['overflow'])} élément(s) hors écran, "
                f"dont {m['overflow'][0]['tag']}.{m['overflow'][0]['cls']} "
                f"(bord droit à {m['overflow'][0]['right']} px pour "
                f"{m['viewport']} px d'écran) — « {m['overflow'][0]['text']} »")


def test_cibles_tactiles_de_la_barre():
    """Les icônes de la barre fixe se visent au doigt, sans libellé pour aider."""
    missing = _deps_missing()
    if missing:
        _skip(missing)
    for width in WIDTHS:
        m = layout('index.html', width)
        assert not m['smallTargets'], (
            f"index.html à {width} px : cible(s) tactile(s) sous {MIN_TOUCH} px "
            f"dans la barre du haut : {m['smallTargets']}")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    passed = failures = skipped = 0
    for t in tests:
        name = t.__name__[5:].replace('_', ' ')
        try:
            t()
            passed += 1
            print(f'  ok      {name}')
        except Skipped as e:
            skipped += 1
            print(f'  ignoré  {name} : {e}')
        except AssertionError as e:
            failures += 1
            print(f'  ÉCHEC   {name}\n          {e}')
    summary = f'{passed}/{len(tests)} tests passés'
    if skipped:
        summary += f', {skipped} ignoré(s) faute de navigateur'
    print(f'\n{summary}')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
