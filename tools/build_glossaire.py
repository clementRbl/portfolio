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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'tools' / 'glossaire.json'
PAGE = ROOT / 'glossaire.html'
INDEX = ROOT / 'assets' / 'glossaire.json'
MODELE = ROOT / 'rapport.html'

URL = 'https://clement-reboul.fr/portfolio/'


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


def entree(t, par_id):
    """Une entrée : le terme, ses synonymes, les deux niveaux, les renvois."""
    alias = [a for a in t.get('alias', []) if a.lower() != t['terme'].lower()]
    bloc = [f'<article class="entree" id="{e(t["id"])}" '
            f'data-cle="{e(" ".join([t["terme"]] + t.get("alias", [])).lower())}">']
    bloc.append(f'  <h3>{e(t["terme"])}'
                f'<a class="lien-ancre" href="#{e(t["id"])}" '
                f'aria-label="Lien vers la définition de {e(t["terme"])}">#</a></h3>')
    if alias:
        bloc.append(f'  <p class="alias">aussi&nbsp;: {e(", ".join(alias))}</p>')
    bloc.append(f'  <p class="simple">{e(t["simple"])}</p>')
    bloc.append('  <details class="detail"><summary>En détail</summary>'
                f'<p>{e(t["detail"])}</p></details>')

    renvois = []
    for v in t.get('voir', []):
        renvois.append(f'<a href="#{e(v)}">{e(par_id[v]["terme"])}</a>')
    pieds = []
    if renvois:
        pieds.append('<span class="voir">Voir aussi&nbsp;: ' + ' · '.join(renvois) + '</span>')
    if t.get('ou'):
        pieds.append(f'<a class="ou" href="{URL}#{e(t["ou"])}">Où ça sert sur le site →</a>')
    if pieds:
        bloc.append('  <p class="renvois">' + ' '.join(pieds) + '</p>')
    bloc.append('</article>')
    return '\n'.join(bloc)


def construit_page(g):
    csp, palettes, amorce = chrome()
    par_id = {t['id']: t for t in g['termes']}
    n = len(g['termes'])

    puces, sections = [], []
    for f in g['familles']:
        termes = [t for t in g['termes'] if t['famille'] == f['id']]
        if not termes:
            continue
        termes.sort(key=lambda t: t['terme'].lower())
        puces.append(f'<a href="#f-{e(f["id"])}" data-fam="{e(f["id"])}">{e(f["nom"])} '
                     f'<span class="n">{len(termes)}</span></a>')
        corps = '\n'.join(entree(t, par_id) for t in termes)
        sections.append(
            f'<section class="famille" id="f-{e(f["id"])}" data-fam="{e(f["id"])}">\n'
            f'  <h2>{e(f["nom"])}</h2>\n'
            f'  <p class="fam-intro">{e(f["intro"])}</p>\n'
            f'{corps}\n</section>')

    return f"""<!DOCTYPE html>
<html lang="fr" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<!-- Page générée par tools/build_glossaire.py depuis tools/glossaire.json.
     Ne pas éditer à la main : la prochaine construction écraserait la
     correction. Le texte des définitions vit dans le JSON. -->
{csp}
<title>Glossaire - Clément Reboul</title>
<meta name="description" content="Glossaire du portfolio : {n} termes de machine learning, MLOps, GenAI et RAG expliqués en clair, avec le détail technique pour qui veut aller plus loin.">
<link rel="canonical" href="{URL}glossaire.html">
<meta name="robots" content="index, follow">
<meta property="og:type" content="article">
<meta property="og:locale" content="fr_FR">
<meta property="og:url" content="{URL}glossaire.html">
<meta property="og:title" content="Glossaire - le vocabulaire du portfolio expliqué">
<meta property="og:description" content="{n} termes de machine learning, MLOps et GenAI expliqués en clair, avec le détail technique pour qui veut aller plus loin.">
<meta property="og:image" content="{URL}assets/og-clement-reboul.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{URL}assets/og-clement-reboul.png">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' fill='%230A0D0B'/%3E%3Ctext y='72' x='50' font-size='68' text-anchor='middle' fill='%23E4A34B' font-family='Georgia,serif'%3EG%3C/text%3E%3C/svg%3E">
{amorce}
<style>
  /* Palettes reprises de rapport.html à la construction : une seule définition
     pour tout le site, aucune copie à tenir à jour. */
{palettes}
  *{{box-sizing:border-box;}}
  html{{scroll-behavior:smooth;}}
  body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--font-sans);font-size:17px;line-height:1.7;-webkit-font-smoothing:antialiased;}}
  @media (prefers-reduced-motion: reduce){{html{{scroll-behavior:auto;}}}}

  .topbar{{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--border);}}
  .topbar-in{{max-width:900px;margin-inline:auto;padding:0 24px;height:58px;display:flex;align-items:center;gap:16px;}}
  .back{{display:inline-flex;align-items:center;gap:8px;text-decoration:none;color:var(--ink-soft);font-weight:600;font-size:14.5px;}}
  .back:hover{{color:var(--accent);}}
  .back svg{{width:16px;height:16px;}}
  .topbar .tt{{margin-left:auto;font-family:var(--font-mono);font-size:12.5px;color:var(--muted);letter-spacing:.04em;text-transform:uppercase;}}
  .icon-btn{{background:var(--surface);border:1px solid var(--border);color:var(--ink);width:36px;height:36px;border-radius:6px;cursor:pointer;display:grid;place-items:center;}}
  .icon-btn svg{{width:17px;height:17px;}}
  .theme-sun{{display:none;}} html[data-theme="light"] .theme-sun{{display:block;}} html[data-theme="light"] .theme-moon{{display:none;}}
  a{{color:var(--accent);}}
  :focus-visible{{outline:2px solid var(--accent);outline-offset:2px;}}

  main{{max-width:900px;margin-inline:auto;padding:52px 24px 100px;}}
  h1{{font-size:2.3rem;line-height:1.15;margin:0 0 14px;letter-spacing:-.02em;}}
  .chapo{{color:var(--ink-soft);font-size:17.5px;margin:0 0 8px;max-width:62ch;}}

  /* Filtre : caché tant que le script n'a pas pris la main, pour ne pas
     proposer un champ inerte à qui navigue sans JavaScript. */
  .filtre{{margin:26px 0 8px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;}}
  .filtre input{{
    flex:1;min-width:230px;background:var(--surface);border:1px solid var(--border);
    border-radius:9px;padding:12px 14px;color:var(--ink);font-family:var(--font-sans);font-size:16px;
  }}
  .filtre input::placeholder{{color:var(--muted);}}
  .filtre input:focus{{outline:2px solid var(--accent);outline-offset:1px;border-color:transparent;}}
  .compte{{font-family:var(--font-mono);font-size:12.5px;color:var(--muted);letter-spacing:.04em;}}

  .puces{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 34px;}}
  .puces a{{
    display:inline-flex;align-items:center;gap:7px;text-decoration:none;
    font-family:var(--font-mono);font-size:12px;letter-spacing:.05em;text-transform:uppercase;
    color:var(--ink-soft);background:var(--surface);border:1px solid var(--border);
    border-radius:999px;padding:7px 13px;
  }}
  .puces a:hover{{border-color:var(--accent);color:var(--accent);}}
  .puces .n{{font-size:11px;color:var(--muted);}}
  /* La famille affichée se distingue nettement : sans marque d'état, on ne sait
     plus quelle page on lit ni pourquoi les autres termes ont disparu. */
  .puces a[aria-current="page"]{{
    background:var(--accent);border-color:var(--accent);color:var(--accent-ink);
  }}
  .puces a[aria-current="page"] .n{{color:var(--accent-ink);opacity:.75;}}

  .puces.inerte a{{opacity:.45;}}
  .pagination{{
    display:flex;align-items:center;justify-content:space-between;gap:14px;
    margin:34px 0 0;padding-top:20px;border-top:1px solid var(--border);
  }}
  .pg{{
    background:var(--surface);border:1px solid var(--border);color:var(--ink);
    border-radius:9px;padding:10px 16px;cursor:pointer;font-family:var(--font-sans);
    font-size:14.5px;font-weight:600;
  }}
  .pg:hover:not(:disabled){{border-color:var(--accent);color:var(--accent);}}
  .pg:disabled{{opacity:.4;cursor:not-allowed;}}
  .pg-etat{{font-family:var(--font-mono);font-size:12.5px;color:var(--muted);text-align:center;}}

  .famille{{margin:0 0 12px;scroll-margin-top:74px;}}
  .famille h2{{font-size:1.4rem;margin:38px 0 4px;letter-spacing:-.01em;}}
  .fam-intro{{color:var(--muted);margin:0 0 18px;font-size:15.5px;}}

  .entree{{
    border:1px solid var(--border);border-left:3px solid var(--border-strong);
    border-radius:10px;padding:18px 20px;margin:0 0 12px;background:var(--surface);
    scroll-margin-top:74px;
  }}
  .entree:target{{border-left-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 16%,transparent);}}
  .entree h3{{font-size:1.12rem;margin:0;display:flex;align-items:baseline;gap:9px;}}
  .lien-ancre{{text-decoration:none;color:var(--muted);font-family:var(--font-mono);font-size:13px;opacity:0;transition:opacity .15s;}}
  .entree:hover .lien-ancre,.lien-ancre:focus-visible{{opacity:1;}}
  .alias{{margin:4px 0 0;font-family:var(--font-mono);font-size:12px;color:var(--muted);letter-spacing:.03em;}}
  .simple{{margin:10px 0 0;color:var(--ink-soft);}}
  .detail{{margin-top:11px;}}
  .detail summary{{
    cursor:pointer;font-family:var(--font-mono);font-size:12px;letter-spacing:.09em;
    text-transform:uppercase;color:var(--accent);width:max-content;
  }}
  .detail summary::marker{{color:var(--muted);}}
  .detail p{{margin:9px 0 0;color:var(--ink-soft);font-size:16px;border-left:2px solid var(--border);padding-left:14px;}}
  .renvois{{margin:12px 0 0;font-size:14px;display:flex;flex-wrap:wrap;gap:6px 18px;color:var(--muted);}}
  .renvois a{{text-decoration:none;}}
  .renvois a:hover{{text-decoration:underline;}}
  .ou{{font-family:var(--font-mono);font-size:12.5px;}}

  .vide{{display:none;padding:30px 4px;color:var(--muted);}}
  .vide.on{{display:block;}}

  @media (max-width: 620px){{
    body{{font-size:16px;}}
    main{{padding:32px 16px 72px;}}
    .topbar-in{{padding:0 14px;height:52px;gap:10px;}}
    .back{{font-size:0;gap:0;}}
    .back svg{{width:20px;height:20px;}}
    .topbar .tt{{font-size:10.5px;letter-spacing:.02em;}}
    .icon-btn{{width:40px;height:40px;flex:none;}}
    h1{{font-size:1.75rem;}}
    .entree{{padding:15px 16px;}}
    .entree h3{{font-size:1.05rem;}}
    .pg{{padding:12px 14px;font-size:13.5px;}}
    .pg-etat{{font-size:11px;}}
  }}
  @media print{{.topbar,.filtre,.puces,.pagination{{display:none;}}
    .famille[hidden]{{display:block !important;}}main{{max-width:none;padding:0;}}
    .entree{{break-inside:avoid;}} .detail[open] summary{{display:none;}} body{{font-size:11pt;}}}}
</style>
<!-- Analytics Umami (cookieless, sans bannière) -->
<script defer src="https://cloud.umami.is/script.js" data-website-id="d6a8ee08-52c7-4346-96f9-3fccf5c0fa87"></script>
</head>
<body>
<div class="topbar"><div class="topbar-in">
  <a class="back" href="{URL}" aria-label="Retour au portfolio"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M19 12H5M11 6l-6 6 6 6"/></svg> Retour au portfolio</a>
  <span class="tt">Glossaire</span>
  <button class="icon-btn" id="tg" aria-label="Basculer le thème">
    <svg class="theme-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
    <svg class="theme-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4.4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.5 1.5M17.6 17.6l1.5 1.5M19.1 4.9l-1.5 1.5M6.4 17.6l-1.5 1.5"/></svg>
  </button>
</div></div>
<main>
<h1>Glossaire</h1>
<p class="chapo">Le vocabulaire employé sur ce portfolio et dans le rapport, {n} termes,
expliqués d'abord en clair puis en détail pour qui veut aller plus loin. Aucune
connaissance préalable n'est supposée par le premier niveau.</p>
<p class="chapo">Un mot vous manque en lisant une page&nbsp;? Il est probablement ici.</p>

<div class="filtre" hidden id="filtre">
  <label class="sr" for="q" hidden>Filtrer les termes</label>
  <input id="q" type="search" autocomplete="off" placeholder="Filtrer : drift, SHAP, seuil…">
  <span class="compte" id="compte" role="status" aria-live="polite"></span>
</div>

<nav class="puces" aria-label="Familles de termes">
  <a href="#" id="puce-toutes" aria-current="page">Toutes <span class="n">{n}</span></a>
{chr(10).join('  ' + p for p in puces)}
</nav>

{chr(10).join(sections)}

<p class="vide" id="vide">Aucun terme ne correspond. Essayez un mot plus court, ou parcourez les familles ci-dessus.</p>

<nav class="pagination" id="pagination" hidden aria-label="Navigation entre les familles">
  <button type="button" id="prec" class="pg">← Précédent</button>
  <span class="pg-etat" id="pg-etat" role="status" aria-live="polite"></span>
  <button type="button" id="suiv" class="pg">Suivant →</button>
</nav>
</main>

<script>
(function () {{
  "use strict";
  /* Thème : même bascule et même stockage que le portfolio et le rapport. */
  var btn = document.getElementById('tg');
  var jeu = document.documentElement.classList.contains('fx-game');
  if (btn) {{
    if (jeu) {{
      btn.setAttribute('aria-disabled', 'true');
      btn.title = 'Le mode Game impose le thème sombre';
    }} else {{
      btn.addEventListener('click', function () {{
        var t = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', t);
        try {{ localStorage.setItem('theme', t); }} catch (e) {{}}
      }});
    }}
  }}

  /* Cent vingt-sept entrées d'un seul tenant, c'était une page qu'on fait
     défiler sans fin pour trouver un mot. Deux réglages indépendants s'en
     chargent : les pastilles filtrent par famille, et la liste obtenue est
     découpée en pages de taille fixe. Découper par famille seule ne suffisait
     pas - la plus fournie en compte vingt et une, soit six écrans.

     La barre de recherche, elle, balaie toujours les cent vingt-sept termes,
     quelle que soit la page affichée : chercher dans la page courante n'aurait
     aucun sens.

     Sans script, tout reste affiché : la pagination est un confort de lecture,
     pas une condition d'accès. */
  var PAR_PAGE = 10;

  var boite = document.getElementById('filtre');
  var champ = document.getElementById('q');
  var compte = document.getElementById('compte');
  var vide = document.getElementById('vide');
  var pagination = document.getElementById('pagination');
  var etat = document.getElementById('pg-etat');
  var btnPrec = document.getElementById('prec');
  var btnSuiv = document.getElementById('suiv');
  var entrees = [].slice.call(document.querySelectorAll('.entree'));
  var familles = [].slice.call(document.querySelectorAll('.famille'));
  var puces = [].slice.call(document.querySelectorAll('.puces a[data-fam]'));
  var puceToutes = document.getElementById('puce-toutes');
  if (!champ || !familles.length) return;
  boite.hidden = false;
  pagination.hidden = false;

  var famille = null;   // null = toutes
  var page = 0;

  function sansAccent(s) {{
    return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }}

  /* Les termes retenus par les deux réglages, dans l'ordre de la page. */
  function retenus() {{
    var q = sansAccent(champ.value.trim());
    /* Une recherche porte sur la totalité du glossaire, jamais sur la seule
       famille affichée : on cherche un mot parce qu'on ignore où il se range.
       Le filtre par famille est donc levé dès qu'une requête est saisie. */
    return entrees.filter(function (el) {{
      if (!q && famille && el.closest('.famille').getAttribute('data-fam') !== famille) return false;
      if (!q) return true;
      return sansAccent(el.getAttribute('data-cle') + ' ' + el.textContent).indexOf(q) !== -1;
    }});
  }}

  function rendre() {{
    var liste = retenus();
    var pages = Math.max(1, Math.ceil(liste.length / PAR_PAGE));
    if (page >= pages) page = pages - 1;
    var debut = page * PAR_PAGE;
    var visibles = liste.slice(debut, debut + PAR_PAGE);

    entrees.forEach(function (el) {{ el.hidden = visibles.indexOf(el) === -1; }});
    /* Un titre de famille sans terme dessous n'a rien à dire : il ne reste que
       si la page en cours contient au moins une de ses entrées. */
    familles.forEach(function (f) {{ f.hidden = !f.querySelector('.entree:not([hidden])'); }});

    var enRecherche = !!champ.value.trim();
    puces.forEach(function (a) {{
      if (!enRecherche && a.getAttribute('data-fam') === famille) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    }});
    if (puceToutes) {{
      if (!enRecherche && famille === null) puceToutes.setAttribute('aria-current', 'page');
      else puceToutes.removeAttribute('aria-current');
    }}
    /* Pendant une recherche, les pastilles ne filtrent plus rien : les griser
       évite de laisser croire à un filtre actif qui ne s'applique pas. */
    var nav = document.querySelector('.puces');
    if (nav) nav.classList.toggle('inerte', enRecherche);

    vide.classList.toggle('on', liste.length === 0);
    pagination.hidden = liste.length === 0;

    var q = champ.value.trim();
    if (q) {{
      compte.textContent = liste.length === 0 ? 'aucun résultat'
        : liste.length + (liste.length > 1 ? ' résultats' : ' résultat') + ' sur {n}';
    }} else {{
      compte.textContent = liste.length + (liste.length > 1 ? ' termes' : ' terme')
        + (famille ? ' dans cette famille' : ' au total');
    }}
    etat.textContent = 'Page ' + (page + 1) + ' sur ' + pages;
    btnPrec.disabled = page === 0;
    btnSuiv.disabled = page >= pages - 1;
  }}

  function remonter() {{
    var haut = document.querySelector('.puces');
    if (haut) haut.scrollIntoView({{ block: 'start' }});
  }}

  puces.forEach(function (a) {{
    a.addEventListener('click', function (ev) {{
      ev.preventDefault();
      var f = a.getAttribute('data-fam');
      // Choisir une famille pendant une recherche efface celle-ci : les deux
      // réglages se contrediraient, et le clic semblerait sans effet.
      if (champ.value) champ.value = '';
      famille = (famille === f) ? null : f;   // recliquer la famille active la désélectionne
      page = 0;
      rendre();
      remonter();
    }});
  }});
  if (puceToutes) {{
    puceToutes.addEventListener('click', function (ev) {{
      ev.preventDefault(); champ.value = ''; famille = null; page = 0; rendre(); remonter();
    }});
  }}
  btnPrec.addEventListener('click', function () {{ page--; rendre(); remonter(); }});
  btnSuiv.addEventListener('click', function () {{ page++; rendre(); remonter(); }});

  /* Une recherche repart de la première page : rester en page 4 d'un résultat
     qui en compte deux donnerait une page vide sans raison apparente. */
  champ.addEventListener('input', function () {{ page = 0; rendre(); }});
  champ.addEventListener('keydown', function (e) {{
    if (e.key === 'Escape' && champ.value) {{ champ.value = ''; page = 0; rendre(); }}
  }});

  /* Les liens du rapport visent un terme précis, que le filtre ou la pagination
     placent peut-être hors de la page affichée. On lève donc tous les réglages
     et on ouvre la page qui contient la cible - sans quoi soixante-huit liens
     aboutiraient à une page où le terme est introuvable. */
  function suivreAncre(defiler) {{
    var id = location.hash.slice(1);
    if (!id) return;
    var cible = document.getElementById(id);
    if (!cible) return;

    if (cible.classList.contains('famille')) {{
      famille = cible.getAttribute('data-fam');
      champ.value = ''; page = 0; rendre();
      if (defiler) cible.scrollIntoView({{ block: 'start' }});
      return;
    }}
    if (!cible.classList.contains('entree')) return;

    champ.value = '';
    famille = null;
    var rang = entrees.indexOf(cible);
    page = Math.floor(rang / PAR_PAGE);
    rendre();
    // Venir d'un lien du rapport, c'est chercher la précision technique.
    var d = cible.querySelector('details');
    if (d) d.open = true;
    if (defiler) cible.scrollIntoView({{ block: 'start' }});
  }}

  window.addEventListener('hashchange', function () {{ suivreAncre(true); }});

  rendre();
  suivreAncre(true);
}})();
</script>
</body>
</html>
"""


def construit_index(g):
    """Forme compacte pour la palette : de quoi filtrer et afficher, rien de plus."""
    fam = {f['id']: f['nom'] for f in g['familles']}
    return [{'id': t['id'], 't': t['terme'], 'f': fam[t['famille']],
             'a': t.get('alias', []), 's': t['simple']}
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
