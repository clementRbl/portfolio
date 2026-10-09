#!/usr/bin/env python3
"""Construit le contenu de rapport.html à partir de tools/rapport/rapport.md.

    python3 tools/rapport/charts.py      # si les chiffres des graphiques changent
    python3 tools/build_rapport.py
    python3 tools/link_glossaire.py      # repose les liens du glossaire

Seul le contenu de <main> est régénéré : l'en-tête, les styles, la barre du haut
et le script de thème de rapport.html restent tels quels. Pandoc convertit le
Markdown ; chaque commentaire « <!-- figure: nom | légende --> » devient une
figure dont le SVG (tools/rapport/figures/nom.svg) est inséré dans la page, pour
qu'il prenne les couleurs du thème actif.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "rapport.html"
SOURCE = ROOT / "tools" / "rapport" / "rapport.md"
FIGURES = ROOT / "tools" / "rapport" / "figures"

# Exemple : <!-- figure: architecture | Architecture de la V2 : ... -->
FIGURE_MARK = re.compile(r"<!-- figure: ([\w-]+) \| (.+?) -->")
# Pandoc écrit « <table> » ou « <table style=...> »
TABLE_OPEN = re.compile(r"<table(\s[^>]*)?>")


def markdown_to_html(markdown: Path) -> str:
    result = subprocess.run(
        ["pandoc", "--from=markdown", "--to=html", "--wrap=none", str(markdown)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def insert_figure(match: re.Match) -> str:
    name, caption = match.group(1), match.group(2)
    svg = (FIGURES / f"{name}.svg").read_text(encoding="utf-8").strip()
    return f'<figure class="fig">\n{svg}\n<figcaption>{caption}</figcaption>\n</figure>'


def main() -> None:
    body = FIGURE_MARK.sub(insert_figure, markdown_to_html(SOURCE))
    # Sur mobile, un tableau large défile dans son cadre au lieu d'élargir la page.
    body = TABLE_OPEN.sub(lambda m: f'<div class="tablewrap">{m.group(0)}', body)
    body = body.replace("</table>", "</table></div>")
    if "<!-- figure:" in body:
        raise SystemExit("Figure mal écrite : attendu <!-- figure: nom | légende -->")

    page = PAGE.read_text(encoding="utf-8")
    start = page.index("<main>") + len("<main>")
    end = page.index("</main>")
    PAGE.write_text(page[:start] + "\n" + body + page[end:], encoding="utf-8")
    print(f"{PAGE.name} régénéré depuis {SOURCE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
