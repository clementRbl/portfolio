#!/usr/bin/env python3
"""Fabrique les images du portfolio à partir des livrables d'origine.

Le site n'a pas d'étape de build : les fichiers d'assets/ sont servis tels
quels. Ce script existe pour que chaque image reste traçable - on sait de quel
projet, de quel notebook et de quelle figure elle sort - et pour que la même
recette produise deux fois le même fichier.

    python3 tools/build_images.py                 # tout sauf les figures Plotly
    uv run --with plotly --with kaleido \
        python3 tools/build_images.py             # tout

Les sources vivent hors du dépôt, dans les projets eux-mêmes (Livrables/), donc
le script ne tourne que sur la machine qui les héberge. Une source absente est
signalée et sautée : le reste se construit quand même.

Recette d'une entrée de tools/images.json :

    from   file      un fichier image
           notebook  la n-ième sortie image/png d'un .ipynb
           plotly    la n-ième figure Plotly d'un .ipynb, rendue en PNG
    crop   [l, h, ancrage] ou [l, h, ancrage, dx, dy] : découpe appliquée à
           la source, avant redimension
    fit    cover (défaut) remplit le cadre, contain fait tenir la figure
           entière et complète avec la couleur de fond de la figure
    size   [l, h] du fichier produit
    colors palette réduite - pour les captures de texte, servies en PNG

ImageMagick fait le travail d'image : c'est un outil système, pas une
dépendance Python, ce qui garde le dépôt sans rien à installer.
"""
import base64, json, re, shutil, struct, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVRABLES = ROOT.parent.parent          # portfolio/ -> falDatacorps/ -> Livrables/
ASSETS = ROOT / 'assets'
QUALITY = 82                            # WebP : au-delà, le poids monte sans gain visible


def convert(*args):
    exe = shutil.which('magick') or shutil.which('convert')
    if not exe:
        sys.exit('ImageMagick est requis : sudo apt install imagemagick')
    cmd = [exe, 'convert'] if exe.endswith('magick') else [exe]
    subprocess.run(cmd + [str(a) for a in args], check=True)


def png_size(raw):
    return struct.unpack('>II', raw[16:24])


def notebook_pngs(path):
    """Sorties image/png d'un notebook, dans l'ordre d'apparition."""
    nb = json.loads(path.read_text(encoding='utf-8'))
    out = []
    for cell in nb.get('cells', []):
        for o in cell.get('outputs', []):
            b64 = o.get('data', {}).get('image/png')
            if b64:
                out.append(base64.b64decode(b64))
    return out


def plotly_pngs(path, width, height):
    """Figures Plotly d'un notebook, re-rendues en PNG à la taille demandée.

    Les notebooks stockent la figure en JSON, pas en image : elle est donc
    régénérée à partir des données d'origine, pas recadrée depuis une capture.
    Le template embarqué est écarté - il embarque des types de traces que les
    versions récentes de Plotly ne reconnaissent plus.
    """
    try:
        import plotly.graph_objects as go, plotly.io as pio
    except ImportError:
        return None
    nb = json.loads(path.read_text(encoding='utf-8'))
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        for cell in nb.get('cells', []):
            for o in cell.get('outputs', []):
                spec = o.get('data', {}).get('application/vnd.plotly.v1+json')
                if not spec:
                    continue
                layout = {k: v for k, v in spec.get('layout', {}).items() if k != 'template'}
                fig = go.Figure(data=spec.get('data', []), layout=layout)
                fig.update_layout(width=width, height=height, template='plotly_white')
                f = Path(tmp) / f'{len(out)}.png'
                pio.write_image(fig, f, scale=1)
                out.append(f.read_bytes())
    return out


def resolve(src):
    p = Path(src).expanduser()
    return p if p.is_absolute() else LIVRABLES / src


def build(item, tmpdir):
    w, h = item['size']
    kind, src = item['from'], resolve(item['src'])
    if not src.exists():
        return f"source absente : {item['src']}"

    if kind == 'file':
        raw = src.read_bytes()
    else:
        pool = notebook_pngs(src) if kind == 'notebook' else plotly_pngs(src, w, h)
        if pool is None:
            return 'Plotly absent - relancez avec : uv run --with plotly --with kaleido'
        n = item['n']
        if n > len(pool):
            return f'figure {n} introuvable ({len(pool)} disponibles)'
        raw = pool[n - 1]

    stage = tmpdir / (item['out'] + '.png')
    stage.write_bytes(raw)

    args = [stage]
    crop = item.get('crop')
    if crop:
        cw, ch, gravity = crop[:3]
        dx, dy = (crop + [0, 0])[3:5] if len(crop) > 3 else (0, 0)
        args += ['-gravity', gravity, '-crop', f'{cw}x{ch}+{dx}+{dy}', '+repage']
    if item.get('fit') == 'contain':
        # Fond prélevé sur la figure elle-même : les bandes ajoutées se
        # confondent avec elle au lieu de trancher sur le panneau.
        bg = subprocess.run(
            [shutil.which('magick') or shutil.which('convert'), str(stage),
             '-format', '%[pixel:p{0,0}]', 'info:'],
            capture_output=True, text=True, check=True).stdout.strip()
        args += ['-resize', f'{w}x{h}', '-background', bg,
                 '-gravity', 'center', '-extent', f'{w}x{h}']
    else:
        args += ['-resize', f'{w}x{h}^', '-gravity', 'north',
                 '-extent', f'{w}x{h}']
    # Les captures de texte, à plat et peu colorées, pèsent moins en PNG
    # quantifié qu'en WebP : le format se choisit donc par image.
    if item.get('colors'):
        args += ['-colors', str(item['colors'])]
    args += ['-strip', '-quality', str(item.get('quality', QUALITY)),
             ASSETS / item['out']]
    convert(*args)
    return None


def main():
    items = json.loads((ROOT / 'tools' / 'images.json').read_text(encoding='utf-8'))
    ASSETS.mkdir(exist_ok=True)
    ok = skipped = 0
    with tempfile.TemporaryDirectory() as tmp:
        for item in items:
            err = build(item, Path(tmp))
            if err:
                skipped += 1
                print(f'  !  {item["out"]:32s} {err}')
                continue
            ok += 1
            f = ASSETS / item['out']
            print(f'  ok {item["out"]:32s} {item["size"][0]}x{item["size"][1]}'
                  f'  {f.stat().st_size / 1024:6.1f} Ko')
    print(f'\n{ok} image(s) construite(s), {skipped} sautée(s)')


if __name__ == '__main__':
    main()
