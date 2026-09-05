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

sys.path.insert(0, str(Path(__file__).resolve().parent))

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


def test_palette_ne_confond_pas_les_mots():
    """La palette cherche des mots entiers, pas des suites de lettres.

    Régression vécue : « RAG » remontait pour « cadrage » et « arbitrage », où
    les trois lettres se trouvent par hasard au milieu du mot. Une recherche de
    vocabulaire qui propose un terme sans rapport perd la confiance du lecteur
    plus sûrement qu'une recherche qui ne trouve rien.
    """
    try:
        from test_responsive import chrome, evalue, BrowserError
    except ImportError:
        return _skip("tools/test_responsive.py est introuvable")
    if not chrome():
        return _skip("Chrome est absent de cette machine")

    expression = """
    (async () => {
      const attendus = {'cadrage': 'Cadrage', 'arbitrage': 'Arbitrage',
                        'SHAP': 'SHAP', 'drift': 'Data drift'};
      const sortie = {};
      const champ = document.getElementById('cmdk-input');
      document.getElementById('wheel-open').click();
      await new Promise(r => setTimeout(r, 1200));
      for (const q of Object.keys(attendus)) {
        champ.value = q;
        champ.dispatchEvent(new Event('input'));
        await new Promise(r => setTimeout(r, 120));
        const groupes = [...document.querySelectorAll('.cmdk-group')].map(e => e.textContent);
        const i = groupes.indexOf('Glossaire');
        const items = [...document.querySelectorAll('.cmdk-item')];
        const glo = i === 0 ? items.slice(0, 6) : [];
        sortie[q] = glo.map(e => e.querySelector('.lb').firstChild.textContent);
      }
      return JSON.stringify(sortie);
    })()
    """
    try:
        res = evalue('index.html', expression)
    except BrowserError as e:
        return _skip(str(e))

    assert 'RAG' not in res['cadrage'], f"« cadrage » remonte encore RAG : {res['cadrage']}"
    assert 'RAG' not in res['arbitrage'], f"« arbitrage » remonte encore RAG : {res['arbitrage']}"
    assert res['cadrage'] and res['cadrage'][0] == 'Cadrage', res['cadrage']
    assert res['SHAP'] and res['SHAP'][0] == 'SHAP', res['SHAP']
    assert 'Data drift' in res['drift'], res['drift']


def _navigateur():
    """Le pilote partagé, ou une raison de sauter le test."""
    try:
        from test_responsive import chrome, evalue, BrowserError
    except ImportError:
        _skip("tools/test_responsive.py est introuvable")
    if not chrome():
        _skip("Chrome est absent de cette machine")
    return evalue, BrowserError


def test_pagination_limite_la_page():
    """La page n'affiche qu'une tranche, pas les cent vingt-sept termes.

    Sans découpage, la page faisait une trentaine d'écrans : on la faisait
    défiler sans fin pour trouver un mot.
    """
    evalue, BrowserError = _navigateur()
    expression = """
    (async () => {
      await new Promise(r => setTimeout(r, 300));
      const affichés = () => [...document.querySelectorAll('.entree')].filter(e => !e.hidden).length;
      const sortie = {total: document.querySelectorAll('.entree').length,
                      page1: affichés(),
                      etat: document.getElementById('pg-etat').textContent,
                      hauteur: document.body.scrollHeight};
      document.getElementById('suiv').click();
      await new Promise(r => setTimeout(r, 120));
      sortie.page2 = affichés();
      sortie.etat2 = document.getElementById('pg-etat').textContent;
      return JSON.stringify(sortie);
    })()
    """
    try:
        r = evalue('glossaire.html', expression)
    except BrowserError as e:
        _skip(str(e))
    assert r['total'] > 100, r['total']
    assert r['page1'] <= 12, f"{r['page1']} entrées sur la première page, c'est trop"
    assert r['page2'] <= 12 and r['page2'] > 0, r['page2']
    assert r['etat'] != r['etat2'], "« Suivant » n'a pas changé de page"
    assert r['hauteur'] < 6000, f"page encore haute de {r['hauteur']} px"


def test_recherche_couvre_tout_le_glossaire():
    """La recherche ignore le filtre de famille et la page affichée.

    Exigence explicite : on cherche un mot précisément parce qu'on ignore dans
    quelle famille il se range. Une recherche cantonnée à la famille affichée
    renverrait un résultat partiel sans prévenir - le pire des deux mondes.
    """
    evalue, BrowserError = _navigateur()
    expression = """
    (async () => {
      const champ = document.getElementById('q');
      const cherche = async (q) => {
        champ.value = q;
        champ.dispatchEvent(new Event('input'));
        await new Promise(r => setTimeout(r, 120));
        return [...document.querySelectorAll('.entree')].filter(e => !e.hidden)
                 .map(e => e.querySelector('h3').textContent.replace('#',''));
      };
      const sortie = {};
      sortie.sansFiltre = await cherche('drift');
      // on sélectionne une famille qui ne contient aucun de ces résultats
      champ.value = '';
      champ.dispatchEvent(new Event('input'));
      const puce = [...document.querySelectorAll('.puces a[data-fam]')]
                     .find(a => /Sécurité/.test(a.textContent));
      puce.click();
      await new Promise(r => setTimeout(r, 120));
      sortie.familleSeule = [...document.querySelectorAll('.entree')].filter(e => !e.hidden).length;
      sortie.avecFiltre = await cherche('drift');
      return JSON.stringify(sortie);
    })()
    """
    try:
        r = evalue('glossaire.html', expression)
    except BrowserError as e:
        _skip(str(e))
    assert len(r['sansFiltre']) >= 5, r['sansFiltre']
    assert r['familleSeule'] > 0, 'le filtre par famille n\'affiche rien'
    assert r['avecFiltre'] == r['sansFiltre'], (
        'la recherche est restée cantonnée à la famille sélectionnée : '
        f"{r['avecFiltre']} au lieu de {r['sansFiltre']}")


def test_lien_du_rapport_atteint_sa_cible():
    """Un terme visé depuis le rapport doit être affiché, pas masqué par la page.

    C'est le risque propre à la pagination : soixante-huit liens du rapport
    visent une ancre que le découpage place ailleurs. Sans levée des réglages,
    ils aboutiraient tous à une page où le terme est introuvable.
    """
    evalue, BrowserError = _navigateur()
    expression = """
    (async () => {
      await new Promise(r => setTimeout(r, 300));
      const cible = document.querySelector(':target');
      return JSON.stringify({
        trouvée: !!cible,
        visible: cible ? (!cible.hidden && !cible.closest('.famille').hidden) : null,
        déplié: cible ? !!cible.querySelector('details[open]') : null
      });
    })()
    """
    for ancre in ('injection-prompt', 'tjm', 'scoring-credit'):
        try:
            r = evalue(f'glossaire.html#{ancre}', expression)
        except BrowserError as e:
            _skip(str(e))
        assert r['trouvée'], f'#{ancre} : ancre absente'
        assert r['visible'], f'#{ancre} : la cible est masquée par la pagination'
        assert r['déplié'], f'#{ancre} : le détail technique n\'est pas déplié'


class Ignore(Exception):
    """Le test n'a pas pu s'exécuter : à ne pas compter comme un succès."""


def _skip(raison):
    try:
        import pytest
        pytest.skip(raison)
    except ImportError:
        raise Ignore(raison)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    echecs = ignores = 0
    for t in tests:
        nom = t.__name__[5:].replace('_', ' ')
        try:
            t()
            print(f'  ok      {nom}')
        except Ignore as e:
            ignores += 1
            print(f'  ignoré  {nom} : {e}')
        except AssertionError as e:
            echecs += 1
            print(f'  ÉCHEC   {nom}\n          {e}')
    bilan = f'{len(tests) - echecs - ignores}/{len(tests)} tests passés'
    if ignores:
        bilan += f', {ignores} ignoré(s) faute de navigateur'
    print(f'\n{bilan}')
    return 1 if echecs else 0


if __name__ == '__main__':
    sys.exit(main())
