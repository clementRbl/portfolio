#!/usr/bin/env python3
"""Construit la page glossaire.html et l'index que consulte la palette.

    python3 tools/build_glossaire.py

Source unique : tools/glossaire.json. Deux sorties, toutes deux commitées et
vérifiées par la CI comme l'est déjà l'index de recherche :

  glossaire.html         la page lisible, une ancre par terme
  assets/glossaire.json  la forme compacte que charge la palette de commandes

Écrire la page à la main aurait voulu dire tenir soixante entrées à deux
niveaux, leurs renvois croisés et leurs ancres sans qu'aucun ne se décale. La
génération rend les renvois vérifiables : un lien cassé arrête la construction
au lieu d'atterrir en ligne.

Les palettes de couleurs et l'amorce de thème ne sont pas recopiées ici : elles
sont relues dans rapport.html à chaque construction. Une page qui s'ouvre depuis
le portfolio ne doit pas donner l'impression d'en sortir, et deux copies d'une
même palette finissent toujours par diverger.
"""
import html
import json
import re
import string
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'tools' / 'glossaire.json'
PAGE = ROOT / 'glossaire.html'
INDEX = ROOT / 'assets' / 'glossaire.json'
MODELE = ROOT / 'rapport.html'

URL = 'https://clement-reboul.fr/portfolio/'   # adresse publique : canonical, og:, JSON-LD
# La navigation interne reste relative. Un href absolu vers la production
# ejecterait le lecteur du serveur local ou de la copie github.io des le
# premier clic - une page ne doit pas dependre du domaine qui la sert.
SITE = 'index.html'


def charge():
    return json.loads(SRC.read_text(encoding='utf-8'))


def verifie(g):
    """Contrôle la cohérence avant d'écrire quoi que ce soit."""
    familles = {f['id'] for f in g['familles']}
    ids = [t['id'] for t in g['termes']]
    doublons = {i for i in ids if ids.count(i) > 1}
    if doublons:
        sys.exit(f'identifiants en double : {sorted(doublons)}')
    connus = set(ids)
    for t in g['termes']:
        if t['famille'] not in familles:
            sys.exit(f"{t['id']} : famille inconnue « {t['famille']} »")
        for champ in ('terme', 'simple', 'detail'):
            if not t.get(champ, '').strip():
                sys.exit(f"{t['id']} : champ « {champ} » vide")
        for v in t.get('voir', []):
            if v not in connus:
                sys.exit(f"{t['id']} : renvoie vers « {v} », qui n'existe pas")
    return g


def chrome():
    """Reprend de rapport.html ce qui doit rester identique d'une page à l'autre."""
    src = MODELE.read_text(encoding='utf-8')
    csp = re.search(r'<meta http-equiv="Content-Security-Policy"[^>]*>', src)
    palettes = re.findall(r'^\s*:root[^\n]*$', src, re.M)
    amorce = re.search(r'<script>\n\(function \(\) \{\n  var m = null;.*?</script>', src, re.S)
    if not (csp and amorce) or len(palettes) < 3:
        sys.exit('rapport.html ne présente plus la structure attendue : '
                 'palettes ou amorce de thème introuvables')
    return csp.group(0), '\n'.join(palettes[:3]), amorce.group(0)


def e(txt):
    return html.escape(txt, quote=True)


def court(nom):
    """Nom de famille abrégé : « MLOps & mise en production » tient mal dans un
    rail de 290 px, et neuf pastilles pleines en occupaient la moitié."""
    return re.split(r'\s*[&,]\s*', nom)[0]


def sans_accent(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower())
                   if unicodedata.category(c) != 'Mn')


def entree(t, par_id, fam_nom):
    """Une fiche : le terme, ses synonymes, les deux niveaux, les renvois.

    Plus de cadre ni de bordure colorée : la fiche occupe seule son volet, la
    typographie suffit à la structurer. L'ancien accordéon « en détail » est
    déplié d'office - il masquait la moitié de ce que le lecteur venait
    chercher derrière un clic, alors que la place ne manque plus.
    """
    alias = [a for a in t.get('alias', []) if a.lower() != t['terme'].lower()]
    b = ['<article class="entree" id="%s" data-fam="%s">' % (e(t['id']), e(t['famille']))]
    b.append('  <p class="fil">%s</p>' % e(fam_nom))
    b.append('  <h2>%s<a class="lien-ancre" href="#%s" aria-label="Lien direct vers %s">#</a></h2>'
             % (e(t['terme']), e(t['id']), e(t['terme'])))
    if alias:
        b.append('  <p class="alias">%s</p>' % e(' · '.join(alias)))
    b.append('  <p class="simple">%s</p>' % e(t['simple']))
    b.append('  <p class="etq">En détail</p>')
    b.append('  <div class="niveau2"><p>%s</p></div>' % e(t['detail']))

    if t.get('voir'):
        liens = ''.join('<a href="#%s">%s</a>' % (e(v), e(par_id[v]['terme'])) for v in t['voir'])
        b.append('  <p class="etq">Voir aussi</p>')
        b.append('  <p class="renvois">%s</p>' % liens)
    if t.get('ou'):
        b.append('  <p class="ou"><a href="%s#%s">Où ça sert sur le site →</a></p>'
                 % (SITE, e(t['ou'])))
    b.append('</article>')
    return '\n'.join(b)


GABARIT = string.Template("""<!DOCTYPE html>
<html lang="fr" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<!-- Page générée par tools/build_glossaire.py depuis tools/glossaire.json.
     Ne pas éditer à la main : la prochaine construction écraserait la
     correction. Le texte des définitions vit dans le JSON. -->
$csp
<title>Glossaire - Clément Reboul</title>
<meta name="description" content="Glossaire du portfolio : $n termes de machine learning, MLOps, GenAI et RAG expliqués en clair, avec le détail technique pour qui veut aller plus loin.">
<link rel="canonical" href="${url}glossaire.html">
<meta name="robots" content="index, follow">
<meta property="og:type" content="article">
<meta property="og:locale" content="fr_FR">
<meta property="og:url" content="${url}glossaire.html">
<meta property="og:title" content="Glossaire - le vocabulaire du portfolio expliqué">
<meta property="og:description" content="$n termes de machine learning, MLOps et GenAI expliqués en clair, avec le détail technique pour qui veut aller plus loin.">
<meta property="og:image" content="${url}assets/og-clement-reboul.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="${url}assets/og-clement-reboul.png">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' fill='%230A0D0B'/%3E%3Ctext y='72' x='50' font-size='68' text-anchor='middle' fill='%23E4A34B' font-family='Georgia,serif'%3EG%3C/text%3E%3C/svg%3E">
$amorce
<style>
  /* Palettes reprises de rapport.html à la construction : une seule définition
     pour tout le site, aucune copie à tenir à jour. */
$palettes
  *{box-sizing:border-box;}
  html{scroll-behavior:smooth;}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--font-sans);font-size:17px;line-height:1.7;-webkit-font-smoothing:antialiased;}
  @media (prefers-reduced-motion: reduce){html{scroll-behavior:auto;}}
  a{color:var(--accent);}
  :focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
  .sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;}

  .topbar{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--border);}
  .topbar-in{max-width:1260px;margin-inline:auto;padding:0 24px;height:58px;display:flex;align-items:center;gap:16px;}
  .back{display:inline-flex;align-items:center;gap:8px;text-decoration:none;color:var(--ink-soft);font-weight:600;font-size:14.5px;}
  .back:hover{color:var(--accent);}
  .back svg{width:16px;height:16px;}
  .topbar .tt{margin-left:auto;font-family:var(--font-mono);font-size:12.5px;color:var(--muted);letter-spacing:.04em;text-transform:uppercase;}
  .icon-btn{background:var(--surface);border:1px solid var(--border);color:var(--ink);width:36px;height:36px;border-radius:6px;cursor:pointer;display:grid;place-items:center;}
  .icon-btn svg{width:17px;height:17px;}
  .theme-sun{display:none;} html[data-theme="light"] .theme-sun{display:block;} html[data-theme="light"] .theme-moon{display:none;}

  /* ---------- DEUX VOLETS ----------
     Cent vingt-sept définitions empilées en pleine largeur, c'était trente
     écrans à faire défiler pour trouver un mot, et un cadre autour de chacune
     pour compenser l'absence de structure. L'index tient maintenant tout à
     gauche, une ligne par terme, et le volet de droite n'affiche que la fiche
     demandée. Chercher un mot ne demande plus de faire défiler quoi que ce
     soit : on le lit dans la liste, ou on le tape.

     Sans script, les deux volets redeviennent un document : tout est affiché,
     dans l'ordre alphabétique. La mise en page est un confort, pas une
     condition d'accès. */
  .gl{max-width:1260px;margin-inline:auto;padding:0 24px;}
  html.gl-js .gl{display:grid;grid-template-columns:290px minmax(0,1fr);align-items:start;}

  .gl-index{padding:22px 0 60px;min-width:0;}
  /* La tête du rail ne défile pas avec la liste : faire descendre les cent
     vingt-sept lignes ne doit pas emporter le champ de recherche hors de vue,
     sans quoi il faut remonter pour corriger un mot. */
  html.gl-js .gl-index{position:sticky;top:58px;height:calc(100dvh - 58px);
    display:flex;flex-direction:column;overflow:hidden;padding-bottom:0;
    padding-right:26px;border-right:1px solid var(--border);}
  html.gl-js .gl-tete{flex:none;}
  html.gl-js .liste-zone{flex:1;min-height:0;overflow-y:auto;overflow-x:hidden;
    overscroll-behavior:contain;padding-bottom:40px;scrollbar-gutter:stable;}

  .gl-cherche{display:flex;align-items:center;gap:9px;background:var(--surface);
    border:1px solid var(--border);border-radius:9px;padding:0 11px;}
  .gl-cherche:focus-within{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 15%,transparent);}
  .gl-cherche svg{width:15px;height:15px;color:var(--muted);flex:none;}
  .gl-cherche input{flex:1;min-width:0;background:none;border:0;outline:0;color:var(--ink);
    font-family:var(--font-sans);font-size:15px;padding:10px 0;}
  .gl-cherche input::placeholder{color:var(--muted);}
  .gl-cherche input::-webkit-search-cancel-button{display:none;}
  .gl-cherche kbd{font-family:var(--font-mono);font-size:11px;color:var(--muted);
    border:1px solid var(--border);border-radius:4px;padding:1px 6px;flex:none;line-height:1.5;}

  .puces{display:flex;flex-wrap:wrap;gap:5px;margin:13px 0 0;}
  .puces button{font-family:var(--font-mono);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;
    background:none;border:1px solid var(--border);color:var(--ink-soft);border-radius:999px;
    padding:4px 9px;cursor:pointer;line-height:1.6;}
  .puces button:hover{border-color:var(--accent);color:var(--accent);}
  .puces button[aria-current="true"]{background:var(--accent);border-color:var(--accent);color:var(--accent-ink);}

  .compte{font-family:var(--font-mono);font-size:10.5px;letter-spacing:.13em;text-transform:uppercase;
    color:var(--muted);margin:18px 0 2px;}

  .liste{list-style:none;margin:0;padding:0;}
  .liste .lettre{font-family:var(--font-mono);font-size:14px;font-weight:700;letter-spacing:.2em;
    color:var(--accent);padding:20px 9px 6px;border-bottom:1px solid var(--border);margin-bottom:5px;}
  .liste .lettre:first-child{padding-top:6px;}
  .liste a{position:relative;display:flex;align-items:baseline;gap:10px;text-decoration:none;
    color:var(--ink-soft);font-size:14.5px;line-height:1.4;padding:5px 9px;border-radius:6px;}
  .liste a:hover{background:var(--surface);color:var(--ink);}
  .liste .lt{min-width:0;overflow-wrap:anywhere;}
  .liste .lf{position:absolute;right:9px;top:50%;transform:translateY(-50%);
    font-family:var(--font-mono);font-size:9.5px;letter-spacing:.08em;white-space:nowrap;
    text-transform:uppercase;color:var(--muted);opacity:0;pointer-events:none;
    padding-left:20px;background:linear-gradient(90deg,transparent,var(--surface) 60%);}
  .liste a:hover .lf{opacity:.85;}
  .liste a[aria-current="true"]{background:color-mix(in srgb,var(--accent) 15%,transparent);
    color:var(--ink);box-shadow:inset 2px 0 0 var(--accent);}
  .liste a[aria-current="true"] .lf{opacity:.85;
    background:linear-gradient(90deg,transparent,color-mix(in srgb,var(--accent) 15%,var(--bg)) 60%);}
  .liste mark{background:none;color:var(--accent);font-weight:700;}
  .vide{color:var(--muted);font-size:14.5px;padding:22px 0;}

  .gl-detail{padding:34px 0 110px;min-width:0;}
  html.gl-js .gl-detail{padding-left:44px;}
  .retour-liste{display:none;background:none;border:0;color:var(--accent);cursor:pointer;
    font-family:var(--font-mono);font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;
    padding:0;margin:0 0 20px;}

  /* Le navigateur défile de lui-même vers l'ancre au chargement, après notre
     remise en haut de page : sans marge réservée, le titre de la fiche passait
     sous la barre fixe. Mesuré à 74 px de défilement pour une barre de 59. */
  .entree,.fam-fiche,.accueil{scroll-margin-top:76px;}
  .fil{font-family:var(--font-mono);font-size:11px;letter-spacing:.15em;text-transform:uppercase;
    color:var(--accent);margin:0 0 12px;}
  .entree h2,.fam-fiche h2{font-size:2rem;line-height:1.14;letter-spacing:-.022em;margin:0;
    display:flex;align-items:baseline;gap:10px;}
  .lien-ancre{text-decoration:none;color:var(--muted);font-family:var(--font-mono);font-size:15px;opacity:0;transition:opacity .15s;}
  .entree:hover .lien-ancre,.lien-ancre:focus-visible{opacity:1;}
  .alias{margin:9px 0 0;font-family:var(--font-mono);font-size:12.5px;color:var(--muted);letter-spacing:.03em;}
  .simple{margin:24px 0 0;font-size:19px;line-height:1.62;color:var(--ink);max-width:64ch;}
  .etq{display:flex;align-items:center;gap:13px;margin:34px 0 10px;
    font-family:var(--font-mono);font-size:10.5px;letter-spacing:.17em;text-transform:uppercase;color:var(--muted);}
  .etq::after{content:"";flex:1;height:1px;background:var(--border);}
  .niveau2 p{margin:0;color:var(--ink-soft);font-size:16.5px;max-width:66ch;}
  .renvois{display:flex;flex-wrap:wrap;gap:7px;margin:0;}
  .renvois a{text-decoration:none;font-size:13.5px;color:var(--ink-soft);background:var(--surface);
    border:1px solid var(--border);border-radius:999px;padding:4px 12px;line-height:1.6;}
  .renvois a:hover{border-color:var(--accent);color:var(--accent);}
  .ou{margin:22px 0 0;}
  .ou a{font-family:var(--font-mono);font-size:12.5px;text-decoration:none;}
  .ou a:hover{text-decoration:underline;}

  .accueil h1{font-size:2.6rem;line-height:1.1;letter-spacing:-.025em;margin:0 0 16px;}
  .chapo{color:var(--ink-soft);font-size:17.5px;margin:0 0 10px;max-width:60ch;}
  .aide{font-family:var(--font-mono);font-size:12px;color:var(--muted);margin:22px 0 0;letter-spacing:.03em;}
  .aide kbd{border:1px solid var(--border);border-radius:4px;padding:1px 6px;color:var(--ink-soft);}
  .fam-grille{display:grid;grid-template-columns:repeat(auto-fill,minmax(258px,1fr));gap:0 40px;margin:30px 0 0;}
  .fam-grille button{display:block;width:100%;text-align:left;background:none;border:0;
    border-top:1px solid var(--border);padding:15px 0;cursor:pointer;color:var(--ink);font-family:inherit;}
  .fam-grille button:hover .fg-n{color:var(--accent);}
  .fg-n{font-size:15.5px;font-weight:700;display:flex;align-items:baseline;gap:9px;}
  .fg-c{font-family:var(--font-mono);font-size:10.5px;color:var(--muted);letter-spacing:.08em;}
  .fg-i{display:block;color:var(--ink-soft);font-size:14px;line-height:1.5;margin-top:5px;}
  .fam-fiche .fam-intro{margin:22px 0 0;font-size:18px;color:var(--ink-soft);max-width:62ch;}

  /* Sous 940 px les deux volets s'empilent, l'accueil d'abord : masquer le
     volet droit privait le lecteur mobile du titre et de l'introduction. Le
     couple grille de familles + pastilles ferait doublon, la grille cède la
     place. Ouvrir un terme, en revanche, remplace bien la liste - c'est une
     lecture, pas un choix. */
  @media (max-width: 939px){
    html.gl-js .gl{display:flex;flex-direction:column;}
    html.gl-js .gl-detail{order:1;padding:22px 0 4px;}
    html.gl-js .gl-index{order:2;position:static;height:auto;overflow:visible;
      border-right:0;padding:4px 0 40px;display:block;}
    html.gl-js .liste-zone{overflow:visible;padding-bottom:0;}
    html.gl-js .gl-tete{display:contents;}
    html.gl-js .gl-cherche{position:sticky;top:66px;z-index:6;
      box-shadow:0 0 0 8px var(--bg);}
    html.gl-js:not(.fiche) .fam-grille,
    html.gl-js:not(.fiche) .aide{display:none;}
    html.gl-js.fiche .gl-index{display:none;}
    html.gl-js.fiche .gl-detail{padding-bottom:90px;}
    html.gl-js.fiche .retour-liste{display:inline-flex;}
  }
  @media (max-width: 620px){
    body{font-size:16px;}
    .gl{padding:0 16px;}
    .topbar-in{padding:0 14px;height:52px;gap:10px;}
    .back{font-size:0;gap:0;}
    .back svg{width:20px;height:20px;}
    .topbar .tt{font-size:10.5px;letter-spacing:.02em;}
    .icon-btn{width:40px;height:40px;flex:none;}
    html.gl-js .gl-cherche{top:60px;}
    .accueil h1{font-size:1.9rem;}
    .entree h2,.fam-fiche h2{font-size:1.5rem;}
    .simple{font-size:17px;}
    .liste a{padding:8px 9px;}
    .liste .lettre{font-size:15px;padding:24px 9px 7px;}
    .fam-grille{grid-template-columns:1fr;gap:0;}
  }
  @media print{
    .topbar,.gl-cherche,.puces,.compte,.retour-liste,.lien-ancre{display:none;}
    .gl{display:block;max-width:none;padding:0;}
    .gl-index{display:none;}
    .entree{break-inside:avoid;} body{font-size:11pt;}
  }
</style>
<!-- Analytics Umami (cookieless, sans bannière) -->
<script defer src="https://cloud.umami.is/script.js" data-website-id="d6a8ee08-52c7-4346-96f9-3fccf5c0fa87"></script>
</head>
<body>
<div class="topbar"><div class="topbar-in">
  <a class="back" href="$site" aria-label="Retour au portfolio"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M19 12H5M11 6l-6 6 6 6"/></svg> Retour au portfolio</a>
  <span class="tt">Glossaire</span>
  <button class="icon-btn" id="tg" aria-label="Basculer le thème">
    <svg class="theme-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
    <svg class="theme-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4.4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.5 1.5M17.6 17.6l1.5 1.5M19.1 4.9l-1.5 1.5M6.4 17.6l-1.5 1.5"/></svg>
  </button>
</div></div>

<div class="gl">
  <aside class="gl-index" aria-label="Index des termes">
   <div class="gl-tete">
    <div class="gl-cherche">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6"/></svg>
      <label class="sr" for="q">Filtrer les termes</label>
      <input id="q" type="search" autocomplete="off" spellcheck="false" placeholder="Filtrer : drift, SHAP, seuil…">
      <kbd>/</kbd>
    </div>
    <nav class="puces" aria-label="Familles de termes">
      <button type="button" data-fam="" aria-current="true">Toutes <span class="n">$n</span></button>
$puces
    </nav>
    <p class="compte" id="compte" role="status" aria-live="polite">$n termes</p>
   </div>
   <div class="liste-zone">
    <ol class="liste" id="liste">
$liste
    </ol>
    <p class="vide" id="vide" hidden>Aucun terme ne correspond. Essayez un mot plus court.</p>
   </div>
  </aside>

  <main class="gl-detail">
    <button type="button" class="retour-liste" id="retour">← Tous les termes</button>
$panneaux
  </main>
</div>

<script>
(function () {
  "use strict";
  /* Thème : même bascule et même stockage que le portfolio et le rapport. */
  var btn = document.getElementById('tg');
  var jeu = document.documentElement.classList.contains('fx-game');
  if (btn) {
    if (jeu) {
      btn.setAttribute('aria-disabled', 'true');
      btn.title = 'Le mode Game impose le thème sombre';
    } else {
      btn.addEventListener('click', function () {
        var t = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', t);
        try { localStorage.setItem('theme', t); } catch (e) {}
      });
    }
  }

  var doc = document.documentElement;
  var champ = document.getElementById('q');
  var liste = document.getElementById('liste');
  var detail = document.querySelector('.gl-detail');
  if (!champ || !liste || !detail) return;

  var lignes = [].slice.call(liste.querySelectorAll('a[data-id]'));
  var lettres = [].slice.call(liste.querySelectorAll('.lettre'));
  var puces = [].slice.call(document.querySelectorAll('.puces button'));
  var compte = document.getElementById('compte');
  var vide = document.getElementById('vide');
  var retour = document.getElementById('retour');

  /* Les panneaux du volet droit : l'accueil, une fiche par famille, une fiche
     par terme. Un seul est visible à la fois - sauf sans script, où ils le
     sont tous et forment un document ordinaire. */
  var panneaux = [].slice.call(detail.querySelectorAll('.accueil, .fam-fiche, .entree'));
  var parId = {};
  panneaux.forEach(function (p) { parId[p.id] = p; });

  /* Le texte cherchable est relu depuis les fiches : aucune copie à tenir dans
     des attributs, et la recherche porte donc bien sur les deux niveaux. */
  var TEXTE = {}, LABEL = {}, NOM = {};
  lignes.forEach(function (a) {
    var id = a.getAttribute('data-id');
    var fiche = parId[id];
    var alias = fiche ? fiche.querySelector('.alias') : null;
    LABEL[id] = a.querySelector('.lt').textContent;
    NOM[id] = sansAccent(LABEL[id] + ' ' + (alias ? alias.textContent : ''));
    TEXTE[id] = sansAccent(a.textContent + ' ' + (fiche ? fiche.textContent : ''));
  });
  var ordreInitial = [].slice.call(liste.children);

  doc.classList.add('gl-js');

  var famille = '';
  var courant = '';

  function sansAccent(s) {
    return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }

  /* Une recherche porte sur la totalité du glossaire, jamais sur la seule
     famille affichée : on cherche un mot parce qu'on ignore où il se range.
     Le filtre de famille est donc levé dès qu'on saisit.

     Les résultats sont classés, et non rendus dans l'ordre alphabétique : taper
     « shap » ouvrait « Biais algorithmique », qui se contente de mentionner la
     méthode et passe avant SHAP dans l'alphabet. Un terme dont le nom ou un
     synonyme commence par ce qu'on tape passe devant ; vient ensuite le nom
     qui le contient ailleurs ; puis seulement les fiches qui en parlent. */
  function retenus() {
    var q = sansAccent(champ.value.trim());
    if (!q) {
      return lignes.filter(function (a) {
        return !famille || a.getAttribute('data-fam') === famille;
      });
    }
    var debut = [], dedans = [], corps = [];
    lignes.forEach(function (a) {
      var id = a.getAttribute('data-id');
      if ((' ' + NOM[id]).indexOf(' ' + q) !== -1) debut.push(a);
      else if (NOM[id].indexOf(q) !== -1) dedans.push(a);
      else if (TEXTE[id].indexOf(q) !== -1) corps.push(a);
    });
    return debut.concat(dedans, corps);
  }

  function amene(l, centre) {
    var zone = l.closest ? l.closest('.liste-zone') : null;
    if (!zone || zone.scrollHeight <= zone.clientHeight + 1) {
      /* Sous 940 px le rail n'a pas son propre défilement : c'est la page. */
      if (centre) l.scrollIntoView({ block: 'center' });
      return;
    }
    var lr = l.getBoundingClientRect(), zr = zone.getBoundingClientRect();
    if (centre) zone.scrollTop += (lr.top - zr.top) - (zr.height - lr.height) / 2;
    else if (lr.top < zr.top) zone.scrollTop += lr.top - zr.top;
    else if (lr.bottom > zr.bottom) zone.scrollTop += lr.bottom - zr.bottom;
  }

  function surligne(a, q) {
    var el = a.querySelector('.lt');
    var t = LABEL[a.getAttribute('data-id')];
    var i = q ? t.toLowerCase().indexOf(q.toLowerCase()) : -1;
    el.textContent = '';
    if (i < 0) { el.textContent = t; return; }
    el.appendChild(document.createTextNode(t.slice(0, i)));
    var m = document.createElement('mark');
    m.textContent = t.slice(i, i + q.length);
    el.appendChild(m);
    el.appendChild(document.createTextNode(t.slice(i + q.length)));
  }

  function rendreIndex() {
    var q = champ.value.trim();
    var classees = retenus();
    var gardes = {};
    classees.forEach(function (a) { gardes[a.getAttribute('data-id')] = 1; });

    var n = 0;
    lignes.forEach(function (a) {
      var on = !!gardes[a.getAttribute('data-id')];
      a.parentNode.hidden = !on;
      if (on) { n++; surligne(a, q); }
    });

    /* L'ordre affiché doit être celui du classement, sinon la flèche bas et la
       touche Entrée ouvriraient autre chose que ce qu'on lit en premier. Les
       lignes retenues sont donc remises dans l'ordre ; hors recherche, la page
       retrouve son classement alphabétique et ses lettres. */
    var frag = document.createDocumentFragment();
    if (q) {
      classees.forEach(function (a) { frag.appendChild(a.parentNode); });
      lettres.forEach(function (l) { l.hidden = true; });
    } else {
      ordreInitial.forEach(function (li) { frag.appendChild(li); });
    }
    liste.appendChild(frag);

    if (!q) {
      /* Une lettre sans terme dessous n'a rien à annoncer. */
      lettres.forEach(function (l) {
        var s = l.nextElementSibling, montre = false;
        while (s && !s.classList.contains('lettre')) {
          if (!s.hidden) { montre = true; break; }
          s = s.nextElementSibling;
        }
        l.hidden = !montre;
      });
    }

    puces.forEach(function (b) {
      var actif = !q && b.getAttribute('data-fam') === famille;
      if (actif) b.setAttribute('aria-current', 'true');
      else b.removeAttribute('aria-current');
    });

    vide.hidden = n > 0;
    compte.textContent = q
      ? (n === 0 ? 'aucun résultat' : n + (n > 1 ? ' résultats' : ' résultat') + ' sur $n')
      : n + (n > 1 ? ' termes' : ' terme') + (famille ? ' dans cette famille' : ' au total');
  }

  function montre(id) {
    courant = parId[id] ? id : '';
    panneaux.forEach(function (p) { p.hidden = p.id !== (courant || 'accueil-gl'); });
    lignes.forEach(function (a) {
      if (a.getAttribute('data-id') === courant) a.setAttribute('aria-current', 'true');
      else a.removeAttribute('aria-current');
    });
    /* Sur mobile l'index occupe l'écran : ouvrir un terme le remplace, et le
       bouton de retour est le seul chemin inverse. Choisir une famille, au
       contraire, filtre la liste - la masquer rendrait le filtre invisible. */
    var terme = !!courant && courant.indexOf('ff-') !== 0;
    doc.classList.toggle('fiche', terme);
    retour.hidden = !terme;
    detail.scrollTop = 0;
    window.scrollTo(0, 0);
  }

  /* L'adresse suit la fiche pour rester copiable, sans empiler d'historique :
     revenir en arrière doit ramener au rapport d'où l'on vient, pas parcourir
     à rebours les vingt termes consultés. */
  function ouvre(id) {
    if (!parId[id]) return false;
    montre(id);
    try { history.replaceState(null, '', '#' + id); } catch (e) {}
    return true;
  }

  lignes.forEach(function (a) {
    a.addEventListener('click', function (ev) {
      ev.preventDefault();
      ouvre(a.getAttribute('data-id'));
    });
  });

  /* Les renvois d'une fiche à l'autre changent de panneau sans recharger. */
  detail.addEventListener('click', function (ev) {
    var a = ev.target.closest ? ev.target.closest('a[href^="#"]') : null;
    if (!a) return;
    var id = a.getAttribute('href').slice(1);
    if (!parId[id]) return;
    ev.preventDefault();
    champ.value = '';
    famille = '';
    rendreIndex();
    ouvre(id);
    var l = lignes.filter(function (x) { return x.getAttribute('data-id') === id; })[0];
    if (l) amene(l, false);
  });

  puces.forEach(function (b) {
    b.addEventListener('click', function () {
      var f = b.getAttribute('data-fam');
      famille = (famille === f) ? '' : f;
      champ.value = '';
      rendreIndex();
      montre(famille ? 'ff-' + famille : '');
      amene(lignes[0], false);
    });
  });

  retour.addEventListener('click', function () { montre(''); });

  champ.addEventListener('input', rendreIndex);
  /* Entrée ouvre le premier résultat : taper « shap » puis Entrée doit suffire. */
  champ.addEventListener('keydown', function (ev) {
    if (ev.key === 'Enter') {
      var r = retenus();
      if (r.length) { ev.preventDefault(); ouvre(r[0].getAttribute('data-id')); }
    }
  });

  function saisie(el) {
    if (!el) return false;
    var t = (el.tagName || '').toLowerCase();
    return t === 'input' || t === 'textarea' || t === 'select' || el.isContentEditable;
  }

  document.addEventListener('keydown', function (ev) {
    if (ev.defaultPrevented) return;
    var raccourci = (ev.key === '/' && !saisie(ev.target))
      || ((ev.metaKey || ev.ctrlKey) && (ev.key === 'k' || ev.key === 'K'));
    if (raccourci) { ev.preventDefault(); champ.focus(); champ.select(); return; }
    if (ev.key === 'Escape') {
      if (champ.value) { champ.value = ''; rendreIndex(); }
      else if (document.activeElement === champ) champ.blur();
      return;
    }
    if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') return;
    if (saisie(ev.target) && ev.target !== champ) return;
    var r = retenus();
    if (!r.length) return;
    ev.preventDefault();
    var i = -1;
    for (var k = 0; k < r.length; k++) { if (r[k].getAttribute('data-id') === courant) { i = k; break; } }
    i = ev.key === 'ArrowDown' ? i + 1 : i - 1;
    if (i < 0) i = 0;
    if (i > r.length - 1) i = r.length - 1;
    ouvre(r[i].getAttribute('data-id'));
    amene(r[i], false);
  });

  /* Les liens du rapport visent un terme précis : on lève tous les réglages
     pour que la cible soit celle qu'on affiche, sans quoi soixante-huit liens
     aboutiraient à une page où le terme reste introuvable. */
  function suivreAncre() {
    var id = location.hash.slice(1);
    if (!parId[id]) { montre(''); return; }
    champ.value = '';
    famille = '';
    rendreIndex();
    montre(id);
    var l = lignes.filter(function (x) { return x.getAttribute('data-id') === id; })[0];
    if (l) amene(l, true);
  }

  window.addEventListener('hashchange', suivreAncre);

  rendreIndex();
  suivreAncre();
})();
</script>
</body>
</html>
""")


def construit_page(g):
    csp, palettes, amorce = chrome()
    par_id = {t['id']: t for t in g['termes']}
    fam_nom = {f['id']: f['nom'] for f in g['familles']}
    n = len(g['termes'])
    par_famille = {f['id']: [t for t in g['termes'] if t['famille'] == f['id']]
                   for f in g['familles']}

    puces = [
        '      <button type="button" data-fam="%s">%s <span class="n">%d</span></button>'
        % (e(f['id']), e(court(f['nom'])), len(par_famille[f['id']]))
        for f in g['familles'] if par_famille[f['id']]
    ]

    # L'index se lit dans l'ordre alphabétique : on y cherche un mot, pas une
    # catégorie. Les familles restent accessibles par les pastilles.
    ordre = sorted(g['termes'], key=lambda t: (sans_accent(t['terme']), t['terme']))
    liste, lettre_en_cours = [], None
    for t in ordre:
        initiale = sans_accent(t['terme'])[:1].upper() or '#'
        if not initiale.isalpha():
            initiale = '#'
        if initiale != lettre_en_cours:
            lettre_en_cours = initiale
            liste.append('      <li class="lettre" aria-hidden="true">%s</li>' % initiale)
        liste.append(
            '      <li><a href="#%s" data-id="%s" data-fam="%s">'
            '<span class="lt">%s</span><span class="lf">%s</span></a></li>'
            % (e(t['id']), e(t['id']), e(t['famille']), e(t['terme']),
               e(court(fam_nom[t['famille']]))))

    grille = [
        '        <button type="button" data-fam="%s">'
        '<span class="fg-n">%s <span class="fg-c">%d</span></span>'
        '<span class="fg-i">%s</span></button>'
        % (e(f['id']), e(f['nom']), len(par_famille[f['id']]), e(f['intro']))
        for f in g['familles'] if par_famille[f['id']]
    ]

    accueil = (
        '    <section class="accueil" id="accueil-gl">\n'
        '      <h1>Glossaire</h1>\n'
        '      <p class="chapo">Le vocabulaire employé sur ce portfolio et dans le rapport, %d termes,\n'
        "      expliqués d'abord en clair puis en détail pour qui veut aller plus loin. Aucune\n"
        '      connaissance préalable n\'est supposée par le premier niveau.</p>\n'
        '      <p class="chapo">Un mot vous manque en lisant une page&nbsp;? Il est probablement ici.</p>\n'
        '      <p class="aide"><kbd>/</kbd> pour chercher · <kbd>↑</kbd><kbd>↓</kbd> pour parcourir · '
        '<kbd>Entrée</kbd> pour ouvrir</p>\n'
        '      <div class="fam-grille">\n%s\n      </div>\n'
        '    </section>' % (n, '\n'.join(grille))
    )

    fiches_fam = [
        '    <section class="fam-fiche" id="ff-%s">\n'
        '      <p class="fil">Famille · %d termes</p>\n'
        '      <h2>%s</h2>\n'
        '      <p class="fam-intro">%s</p>\n'
        '    </section>'
        % (e(f['id']), len(par_famille[f['id']]), e(f['nom']), e(f['intro']))
        for f in g['familles'] if par_famille[f['id']]
    ]

    entrees = ['    ' + entree(t, par_id, fam_nom[t['famille']]).replace('\n', '\n    ')
               for t in ordre]

    return GABARIT.substitute(
        csp=csp, palettes=palettes, amorce=amorce, n=n, url=URL, site=SITE,
        puces='\n'.join(puces),
        liste='\n'.join(liste),
        panneaux='\n'.join([accueil] + fiches_fam + entrees),
    )


def amorce_def(texte):
    """La première phrase de l'explication simple.

    La palette n'affiche que deux lignes : lui envoyer une définition entière
    alourdirait l'index téléchargé sans rien montrer de plus.
    """
    coupe = re.search(r'(?<=[.!?])\s', texte)
    return texte[:coupe.start()].strip() if coupe else texte.strip()


def construit_index(g):
    """Forme compacte pour la palette : de quoi filtrer et afficher, rien de plus."""
    fam = {f['id']: f['nom'] for f in g['familles']}
    return [{'id': t['id'], 't': t['terme'], 'f': fam[t['famille']],
             'a': t.get('alias', []), 's': amorce_def(t['simple'])}
            for t in sorted(g['termes'], key=lambda x: x['terme'].lower())]


def main():
    g = verifie(charge())
    PAGE.write_text(construit_page(g), encoding='utf-8')
    INDEX.write_text(json.dumps(construit_index(g), ensure_ascii=False,
                                separators=(',', ':')), encoding='utf-8')
    print(f'glossaire.html - {len(g["termes"])} termes, {len(g["familles"])} familles, '
          f'{PAGE.stat().st_size / 1024:.1f} Ko')
    print(f'assets/glossaire.json - {INDEX.stat().st_size / 1024:.1f} Ko')


if __name__ == '__main__':
    main()
