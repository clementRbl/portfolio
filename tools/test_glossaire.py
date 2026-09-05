#!/usr/bin/env python3
"""Tests du glossaire : cohérence des données, et liens qui mènent quelque part.

    python3 tools/test_glossaire.py     # sans rien installer
    pytest tools/test_glossaire.py      # si pytest est disponible

Un glossaire se dégrade en silence. Un renvoi vers un terme supprimé, une ancre
qui ne correspond plus, une page régénérée mais non commitée : rien de tout cela
ne casse l'affichage, tout mène le lecteur dans le vide. Ces tests vérifient donc
ce que l'œil ne voit pas en relisant.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = json.loads((ROOT / 'tools' / 'glossaire.json').read_text(encoding='utf-8'))
PAGE = (ROOT / 'glossaire.html').read_text(encoding='utf-8')
RAPPORT = (ROOT / 'rapport.html').read_text(encoding='utf-8')
INDEX = (ROOT / 'index.html').read_text(encoding='utf-8')
COMPACT = json.loads((ROOT / 'assets' / 'glossaire.json').read_text(encoding='utf-8'))

TERMES = SRC['termes']
IDS = {t['id'] for t in TERMES}


def test_identifiants_uniques():
    vus = [t['id'] for t in TERMES]
    doublons = {i for i in vus if vus.count(i) > 1}
    assert not doublons, f'identifiants en double : {sorted(doublons)}'


def test_deux_niveaux_partout():
    """Chaque terme porte bien une explication simple ET un détail technique.

    C'est la promesse faite au lecteur en haut de page : s'il manque un des deux
    niveaux, l'entrée ment sur ce qu'elle offre.
    """
    for t in TERMES:
        for champ in ('simple', 'detail'):
            assert t.get(champ, '').strip(), f"{t['id']} : « {champ} » vide"
        assert t['simple'] != t['detail'], f"{t['id']} : les deux niveaux sont identiques"


def test_familles_connues():
    familles = {f['id'] for f in SRC['familles']}
    for t in TERMES:
        assert t['famille'] in familles, f"{t['id']} : famille « {t['famille']} » inconnue"


def test_renvois_resolvent():
    for t in TERMES:
        for v in t.get('voir', []):
            assert v in IDS, f"{t['id']} renvoie vers « {v} », qui n'existe pas"
            assert v != t['id'], f"{t['id']} se renvoie à lui-même"


def test_sections_citees_existent():
    """Le lien « Où ça sert sur le site » doit viser une section réelle du portfolio."""
    ancres = set(re.findall(r'<section[^>]+id="([\w-]+)"', INDEX))
    ancres |= set(re.findall(r'id="(accueil|contact)"', INDEX))
    for t in TERMES:
        ou = t.get('ou')
        if ou:
            assert ou in ancres, f"{t['id']} : la section « {ou} » n'existe pas dans index.html"


def test_page_a_jour():
    """La page commitée correspond au JSON.

    Elle est générée : si quelqu'un modifie le JSON sans reconstruire, le site
    sert un glossaire qui n'est plus celui du dépôt.
    """
    avant = PAGE
    subprocess.run([sys.executable, str(ROOT / 'tools' / 'build_glossaire.py')],
                   capture_output=True, check=True, cwd=str(ROOT))
    apres = (ROOT / 'glossaire.html').read_text(encoding='utf-8')
    assert avant == apres, ("glossaire.html ne correspond plus à tools/glossaire.json. "
                            "Lancez « python3 tools/build_glossaire.py » et committez.")


def test_une_ancre_par_terme():
    for t in TERMES:
        assert f'id="{t["id"]}"' in PAGE, f"{t['id']} : pas d'ancre dans la page"


def test_index_compact_complet():
    """Ce que charge la palette couvre exactement ce que contient le glossaire."""
    assert {e['id'] for e in COMPACT} == IDS, "assets/glossaire.json ne correspond plus au source"
    for e in COMPACT:
        assert e['t'] and e['s'], f"{e['id']} : entrée compacte incomplète"


def test_liens_du_rapport_aboutissent():
    """Chaque lien posé dans le rapport vise une ancre qui existe vraiment."""
    vises = set(re.findall(r'href="glossaire\.html#([\w-]+)"', RAPPORT))
    assert vises, 'aucun lien de glossaire dans le rapport'
    manquants = vises - IDS
    assert not manquants, f'le rapport renvoie vers des termes inexistants : {sorted(manquants)}'


def test_un_seul_lien_par_terme():
    """Le même terme n'est relié qu'une fois : au-delà, le texte devient illisible."""
    poses = re.findall(r'class="g-lien" href="glossaire\.html#([\w-]+)"', RAPPORT)
    doublons = {i for i in poses if poses.count(i) > 1}
    assert not doublons, f'termes reliés plusieurs fois dans le rapport : {sorted(doublons)}'


def test_liens_du_rapport_a_jour():
    """Le poseur de liens est idempotent : rien à ajouter sur un fichier traité."""
    r = subprocess.run([sys.executable, str(ROOT / 'tools' / 'link_glossaire.py'), '--verifie'],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stdout.strip() or r.stderr.strip()


def test_glossaire_atteignable_depuis_le_site():
    """Une page que rien ne relie n'existe pas pour le visiteur."""
    assert 'glossaire.html' in INDEX, 'aucun lien vers le glossaire dans index.html'
    assert 'glossaire.html' in RAPPORT, 'aucun lien vers le glossaire dans rapport.html'


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    echecs = 0
    for t in tests:
        nom = t.__name__[5:].replace('_', ' ')
        try:
            t()
            print(f'  ok      {nom}')
        except AssertionError as e:
            echecs += 1
            print(f'  ÉCHEC   {nom}\n          {e}')
    print(f'\n{len(tests) - echecs}/{len(tests)} tests passés')
    return 1 if echecs else 0


if __name__ == '__main__':
    sys.exit(main())
