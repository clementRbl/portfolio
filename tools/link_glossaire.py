#!/usr/bin/env python3
"""Relie les termes techniques du rapport à leur définition dans le glossaire.

    python3 tools/link_glossaire.py            # pose les liens manquants
    python3 tools/link_glossaire.py --verifie  # ne modifie rien, sort 1 s'il en manque

Le rapport reste écrit à la main : ce script n'ajoute que les liens, et il est
idempotent - le relancer sur un fichier déjà traité ne change rien. C'est ce que
vérifie la CI, de la même façon qu'elle vérifie l'index de recherche.

Deux règles pour que les liens restent supportables à la lecture :

  - une seule occurrence par terme, la première rencontrée. Souligner les huit
    « MLOps » d'une page transforme le texte en sapin de Noël et n'apprend rien
    de plus au lecteur ;
  - jamais à l'intérieur d'un titre, d'un lien, d'un bloc de code ou du tableau
    de glossaire. Un titre cliquable pour moitié se lit mal, et le code n'est
    pas de la prose.
"""
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CIBLE = ROOT / 'rapport.html'
SRC = ROOT / 'tools' / 'glossaire.json'
GLOSSAIRE = 'glossaire.html'

# Éléments dont le contenu textuel ne doit jamais être transformé.
INTOUCHABLE = ('a', 'code', 'pre', 'h1', 'h2', 'h3', 'h4', 'script', 'style',
               'summary', 'title', 'thead')

# Marque posée sur les liens du script, pour les reconnaître et rester idempotent.
CLASSE = 'g-lien'


@lru_cache(maxsize=1)
def termes():
    """Les termes, du plus long au plus court.

    L'ordre compte : « coût métier asymétrique » doit être essayé avant
    « coût métier », sinon le second mange le début du premier et le lien
    pointe vers une définition moins précise.
    """
    g = json.loads(SRC.read_text(encoding='utf-8'))
    sortie = []
    for t in g['termes']:
        libelles = [t['terme']] + [a for a in t.get('alias', []) if len(a) > 3]
        for lib in libelles:
            sortie.append((lib, t['id']))
    sortie.sort(key=lambda x: -len(x[0]))
    return tuple(sortie)


@lru_cache(maxsize=512)
def motif(libelle):
    """Correspondance sur le mot entier, insensible à la casse et aux variantes."""
    esc = re.escape(libelle).replace(r'\ ', r'[\s ]+').replace(r'\-', r'[-‑]')
    return re.compile(r'(?<![\w-])(' + esc + r')(?![\w-])', re.I)


def transforme(html, poses):
    """Parcourt le document en ne touchant qu'au texte hors éléments interdits."""
    morceaux = re.split(r'(<[^>]*>)', html)
    profondeur = 0
    sortie = []
    for m in morceaux:
        if m.startswith('<'):
            nom = re.match(r'</?\s*([a-zA-Z][\w-]*)', m)
            if nom:
                balise = nom.group(1).lower()
                if balise in INTOUCHABLE:
                    if m.startswith('</'):
                        profondeur = max(0, profondeur - 1)
                    elif not m.rstrip().endswith('/>'):
                        profondeur += 1
            sortie.append(m)
            continue
        if profondeur or not m.strip():
            sortie.append(m)
            continue
        texte = m
        for libelle, ident in termes():
            if ident in poses:
                continue
            trouve = motif(libelle).search(texte)
            if not trouve:
                continue
            lien = (f'<a class="{CLASSE}" href="{GLOSSAIRE}#{ident}" '
                    f'title="Définition dans le glossaire">{trouve.group(1)}</a>')
            texte = texte[:trouve.start()] + lien + texte[trouve.end():]
            poses.add(ident)
            # Le texte contient désormais une balise : on le renvoie au découpage
            # plutôt que d'y chercher un second terme au milieu du lien qu'on
            # vient d'insérer.
            reste = transforme(texte, poses)
            sortie.append(reste)
            break
        else:
            sortie.append(texte)
    return ''.join(sortie)


def main():
    verifie = '--verifie' in sys.argv
    avant = CIBLE.read_text(encoding='utf-8')

    # Le corps seul : ni l'en-tête, ni le chapeau d'introduction, dont les liens
    # sont écrits à la main et n'ont pas à être doublés.
    ancre = avant.find('<div class="chapeau">')
    if ancre == -1:
        sys.exit('rapport.html : chapeau introuvable, structure inattendue')
    debut = avant.index('</div>', ancre) + len('</div>')
    tete, corps = avant[:debut], avant[debut:]

    poses = set(re.findall(rf'class="{CLASSE}" href="{GLOSSAIRE}#([\w-]+)"', corps))
    apres = tete + transforme(corps, poses)

    if apres == avant:
        print(f'rapport.html - {len(poses)} termes déjà reliés, rien à faire')
        return 0
    nouveaux = len(re.findall(rf'class="{CLASSE}"', apres)) - len(re.findall(rf'class="{CLASSE}"', avant))
    if verifie:
        print(f'::error::{nouveaux} lien(s) de glossaire manquant(s) dans rapport.html. '
              'Lancez « python3 tools/link_glossaire.py » et committez le résultat.')
        return 1
    CIBLE.write_text(apres, encoding='utf-8')
    print(f'rapport.html - {nouveaux} lien(s) ajouté(s), '
          f'{len(re.findall(rf"class={chr(34)}{CLASSE}{chr(34)}", apres))} au total')
    return 0


if __name__ == '__main__':
    sys.exit(main())
