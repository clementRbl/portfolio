#!/usr/bin/env python3
"""Dessine les deux graphiques du rapport en SVG, dans tools/rapport/figures/.

    python3 tools/rapport/charts.py

Les SVG n'ont aucune couleur en dur : des classes (c-1, c-2, c-grid...) les
colorent avec les variables du thème de la page, si bien qu'ils suivent les modes
clair, sombre et Game. Les chiffres viennent des exécutions réelles du workflow
de surveillance (dépôt credit-scoring-mlops, reports/month_N/*.json).
"""

from pathlib import Path

FIGURES = Path(__file__).resolve().parent / "figures"

# Surveillance mensuelle du champion v1 : runs 37817647750, 37817766184,
# 37818016873 et 37904674657.
MONTHS = [1, 2, 3, 4]
DRIFT_SHARE = [0.0, 0.0, 35.0, 0.0]  # % des 20 variables surveillées
COST_CHANGE = [1.9, -0.5, 12.5, 45.9]  # % par rapport au coût de référence
DRIFT_ALERT, COST_ALERT = 30, 10

# Coût métier par demande sur les 30 % du mois gardés pour l'évaluation.
DUELS = [
    ("Mois 3", 0.557, 0.5616, "+0,8 % · non promu"),
    ("Mois 4", 0.7418, 0.6816, "−8,1 % · promu"),
]


def fr(value: float, decimals: int = 1) -> str:
    """Nombre au format français : 12,5 ; −0,5."""
    text = f"{abs(value):.{decimals}f}".replace(".", ",")
    return ("−" if value < 0 else "") + text


def bar(x: float, y_base: float, y_top: float, width: float, cls: str, tip: str) -> str:
    """Barre dont seule l'extrémité de donnée est arrondie (4 px), ancrée à la base."""
    r = min(4, abs(y_base - y_top), width / 2)
    if y_top <= y_base:  # valeur positive : arrondi en haut
        d = (
            f"M{x},{y_base} V{y_top + r} Q{x},{y_top} {x + r},{y_top} "
            f"H{x + width - r} Q{x + width},{y_top} {x + width},{y_top + r} "
            f"V{y_base} Z"
        )
    else:  # valeur négative : arrondi en bas
        d = (
            f"M{x},{y_base} V{y_top - r} Q{x},{y_top} {x + r},{y_top} "
            f"H{x + width - r} Q{x + width},{y_top} {x + width},{y_top - r} "
            f"V{y_base} Z"
        )
    return f'<path class="{cls}" d="{d}"><title>{tip}</title></path>'


def panel(
    x0: float, title: str, values: list[float], lo: float, hi: float,
    ticks: list[int], threshold: float, threshold_label: str, unit_sign: bool,
    decimals: int,
) -> list[str]:
    """Un petit graphique en barres : 4 mois, une ligne de seuil, des étiquettes."""
    top, bottom, width = 50, 250, 300
    scale = (bottom - top) / (hi - lo)

    def y(v: float) -> float:
        return round(bottom - (v - lo) * scale, 1)

    out = [f'<text class="c-title" x="{x0}" y="24">{title}</text>']
    for t in ticks:
        out.append(
            f'<line class="{"c-axis" if t == 0 else "c-grid"}" x1="{x0 + 34}" '
            f'x2="{x0 + width}" y1="{y(t)}" y2="{y(t)}"/>'
        )
        label = f"{'+' if unit_sign and t > 0 else ''}{fr(t, 0)} %"
        out.append(
            f'<text class="c-tick" x="{x0 + 28}" y="{y(t) + 4}" '
            f'text-anchor="end">{label}</text>'
        )
    out.append(
        f'<line class="c-thr" x1="{x0 + 34}" x2="{x0 + width}" '
        f'y1="{y(threshold)}" y2="{y(threshold)}"/>'
    )
    # À gauche, au-dessus du mois 1 : la seule zone qu'aucune barre haute n'occupe.
    out.append(
        f'<text class="c-tick" x="{x0 + 40}" y="{y(threshold) - 6}">{threshold_label}</text>'
    )
    slot = (width - 34) / len(values)
    for i, (month, v) in enumerate(zip(MONTHS, values)):
        bx = round(x0 + 34 + i * slot + slot * 0.25, 1)
        bw = round(slot * 0.5, 1)
        sign = "+" if unit_sign and v > 0 else ""
        text = f"{sign}{fr(v, decimals)} %"
        if v != 0:
            out.append(bar(bx, y(0), y(v), bw, "c-2", f"Mois {month} : {text}"))
        label_y = y(max(v, 0)) - 8
        alert = v >= threshold if not unit_sign else v > threshold
        out.append(
            f'<text class="c-lab" x="{bx + bw / 2}" y="{label_y}" '
            f'text-anchor="middle">{text}{" ▲" if alert else ""}</text>'
        )
        out.append(
            f'<text class="c-tick" x="{bx + bw / 2}" y="{bottom + 20}" '
            f'text-anchor="middle">Mois {month}</text>'
        )
    return out


def surveillance() -> str:
    parts = [
        *panel(20, "Variables surveillées qui dérivent", DRIFT_SHARE, 0, 40,
               [0, 10, 20, 30, 40], DRIFT_ALERT, "seuil d'alerte 30 %", False, 0),
        *panel(420, "Variation du coût métier", COST_CHANGE, -10, 50,
               [-10, 0, 10, 20, 30, 40, 50], COST_ALERT, "seuil d'alerte +10 %", True, 1),
    ]
    return svg(
        760, 290, "Surveillance des mois 1 à 4",
        "Mois 3 : 35 % des variables dérivent (alerte). Mois 4 : aucune dérive des "
        "données, mais un coût métier en hausse de 45,9 % (alerte).",
        parts,
    )


def champion_challenger() -> str:
    top, bottom, x_axis, hi = 60, 250, 70, 0.8
    scale = (bottom - top) / hi

    def y(v: float) -> float:
        return round(bottom - v * scale, 1)

    out = [
        '<text class="c-title" x="20" y="24">Coût métier par demande sur des '
        "données jamais vues</text>",
        '<rect class="c-1" x="430" y="13" width="12" height="12" rx="2"/>'
        '<text class="c-tick" x="448" y="23">Champion (en service)</text>',
        '<rect class="c-2" x="600" y="13" width="12" height="12" rx="2"/>'
        '<text class="c-tick" x="618" y="23">Challenger (réentraîné)</text>',
    ]
    for t in [0, 0.2, 0.4, 0.6, 0.8]:
        out.append(
            f'<line class="{"c-axis" if t == 0 else "c-grid"}" x1="{x_axis}" '
            f'x2="740" y1="{y(t)}" y2="{y(t)}"/>'
        )
        out.append(
            f'<text class="c-tick" x="{x_axis - 8}" y="{y(t) + 4}" '
            f'text-anchor="end">{fr(t)}</text>'
        )
    group = (740 - x_axis) / len(DUELS)
    bw = 90
    for i, (name, champion, challenger, verdict) in enumerate(DUELS):
        cx = x_axis + i * group + group / 2
        for value, cls, dx, who in (
            (champion, "c-1", -bw - 1, "Champion"),
            (challenger, "c-2", 1, "Challenger"),
        ):
            bx = round(cx + dx, 1)
            out.append(bar(bx, y(0), y(value), bw, cls, f"{name}, {who} : {fr(value, 3)}"))
            out.append(
                f'<text class="c-lab" x="{bx + bw / 2}" y="{y(value) - 8}" '
                f'text-anchor="middle">{fr(value, 3)}</text>'
            )
        out.append(
            f'<text class="c-tick" x="{cx}" y="{bottom + 20}" '
            f'text-anchor="middle">{name}</text>'
        )
        out.append(
            f'<text class="c-lab" x="{cx}" y="{bottom + 40}" '
            f'text-anchor="middle">{verdict}</text>'
        )
    return svg(
        760, 300, "Champion contre challenger",
        "Mois 3 : 0,557 contre 0,562, non promu. Mois 4 : 0,742 contre 0,682, promu.",
        out,
    )


def svg(width: int, height: int, title: str, desc: str, body: list[str]) -> str:
    inner = "\n  ".join(body)
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{title}. {desc}" xmlns="http://www.w3.org/2000/svg">\n'
        f"  <title>{title}</title>\n  <desc>{desc}</desc>\n  {inner}\n</svg>\n"
    )


if __name__ == "__main__":
    FIGURES.mkdir(exist_ok=True)
    (FIGURES / "surveillance.svg").write_text(surveillance(), encoding="utf-8")
    (FIGURES / "champion-challenger.svg").write_text(
        champion_challenger(), encoding="utf-8"
    )
    print("figures/surveillance.svg et figures/champion-challenger.svg écrits")
