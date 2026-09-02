#!/usr/bin/env python3
"""Tests de régression de la recherche vectorielle du portfolio.

    python3 tools/test_search.py        # sans rien installer
    pytest tools/test_search.py         # si pytest est disponible

Origine : la boîte « Interrogez le CV » proposait la question « Vous travaillez
où ? », qui ne renvoyait rien. Le corpus était écrit au tutoiement (« tu
travailles ») et la racinisation ne connaissait pas la terminaison -ez : les
deux formes tombaient dans deux entrées de vocabulaire distinctes. Rien dans le
dépôt ne pouvait signaler qu'une question proposée au visiteur restait sans
réponse. C'est ce que ces tests vérifient désormais, en lisant les questions
directement dans index.html : en ajouter une sans qu'elle réponde casse le test.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_index import load_index, search, query_tokens, section_of  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / 'index.html').read_text(encoding='utf-8')
INDEX = load_index()
CORPUS = json.loads((ROOT / 'tools' / 'corpus.json').read_text(encoding='utf-8'))


def suggestions():
    """Les questions proposées au visiteur, lues dans la page elle-même."""
    block = re.search(r'var SUGG = \[(.*?)\];', PAGE, re.S)
    assert block, "la liste SUGG est introuvable dans index.html"
    return re.findall(r"'([^']+)'", block.group(1))


def threshold():
    """Le seuil sous lequel la page déclare ne pas savoir répondre."""
    m = re.search(r'top\.score < ([0-9.]+)', PAGE)
    assert m, "le seuil de la boîte « Interrogez le CV » est introuvable"
    return float(m.group(1))


def test_suggestions_trouvees():
    """Chaque question proposée doit obtenir une réponse au-dessus du seuil."""
    seuil = threshold()
    echecs = []
    for q in suggestions():
        connus = [r for r, ok in query_tokens(INDEX, q) if ok]
        hits = search(INDEX, q)
        if not connus or not hits or hits[0][0] < seuil:
            echecs.append((q, connus, hits[0][:2] if hits else None))
    assert not echecs, 'questions proposées sans réponse : %s' % echecs


def test_suggestions_ont_une_reponse_redigee():
    """Une section trouvée sans phrase de réponse afficherait le repli d'échec."""
    reponses = {d['id']: d.get('answer', '') for d in CORPUS}
    for q in suggestions():
        hits = search(INDEX, q)
        assert hits and reponses.get(hits[0][1]), 'pas de réponse rédigée pour « %s »' % q


def test_paraphrases_du_corpus():
    """Les reformulations doivent mener à la bonne section, et le plus souvent
    au bon document.

    Deux mesures, parce que deux choses différentes. Une reformulation qui vise
    « rag » et tombe sur « projets » n'a rien cassé : le visiteur atterrit là
    où se trouve la réponse. Une qui vise « prestations » et tombe sur
    « parcours » l'a envoyé ailleurs. La section est donc l'exigence forte ; le
    document exact mesure la finesse, et se dégrade naturellement quand le
    corpus s'enrichit de documents voisins."""
    total = exact = bonne_section = 0
    egares = []
    for doc in CORPUS:
        cible = doc.get('section', doc['id'])
        for q in doc.get('queries', []):
            total += 1
            hits = search(INDEX, q)
            if not hits:
                egares.append('« %s » ne renvoie rien' % q)
                continue
            if hits[0][1] == doc['id']:
                exact += 1
            if section_of(INDEX, hits[0][1]) == cible:
                bonne_section += 1
    assert total >= 90, 'corpus de reformulations trop maigre : %d' % total
    assert bonne_section / total >= 0.92, (
        'seulement %d/%d reformulations mènent à la bonne section : %s'
        % (bonne_section, total, ' ; '.join(egares[:4])))
    assert exact / total >= 0.72, (
        'seulement %d/%d reformulations trouvent leur propre document' % (exact, total))


def test_vouvoiement_et_tutoiement_convergent():
    """Le site vouvoie, le corpus tutoie : les deux formes doivent se rejoindre."""
    paires = [('vous travaillez', 'tu travailles'),
              ('vous connaissez', 'tu connais'),
              ('vous déployez', 'tu déploies'),
              ('vous êtes disponible', 'tu es disponible')]
    for vous, tu in paires:
        a = search(INDEX, vous)
        b = search(INDEX, tu)
        assert a, 'aucun terme reconnu dans « %s »' % vous
        assert b, 'aucun terme reconnu dans « %s »' % tu
        assert a[0][1] == b[0][1], '« %s » -> %s mais « %s » -> %s' % (vous, a[0][1], tu, b[0][1])


def test_pluriels_preserves():
    """Garde-fou : -ons découperait « missions » en « missi ». Il doit rester absent."""
    for singulier, pluriel in [('mission', 'missions'), ('question', 'questions')]:
        rs = [r for r, _ in query_tokens(INDEX, singulier)]
        rp = [r for r, _ in query_tokens(INDEX, pluriel)]
        assert rs == rp, 'racines divergentes : %s -> %s, %s -> %s' % (singulier, rs, pluriel, rp)


def test_base_ne_capte_pas_base():
    """« base » et « basé » se réduisent à la même racine. Le jour où le corpus
    a gagné « base vectorielle Milvus », « Vous êtes basé où ? » est parti sur
    les projets. Le corpus dit donc « index vectoriel » : ce test le retient."""
    hits = search(INDEX, 'Vous êtes basé où ?')
    assert hits and section_of(INDEX, hits[0][1]) == 'profil', hits[:2]


def test_intentions_connues():
    """Questions courantes et section attendue. Le corpus contient des documents
    thématiques - « rag », « tarifs » - qui répondent pour une section ne portant
    pas leur nom : c'est donc la section visée qu'on compare, pas l'identifiant
    du document. Deux sections peuvent être plausibles ; ces cas-là ont une seule
    bonne réponse et l'ont déjà perdue une fois, quand une reformulation de
    « Parcours » s'est réduite à la même racine que « vous travaillez où »."""
    attendus = [
        ('Vous travaillez où ?', 'profil'),
        ('Vous êtes basé où ?', 'profil'),
        ('Vous acceptez un CDI ?', 'profil'),
        ('Vous êtes disponible ?', 'profil'),
        ('Votre parcours ?', 'parcours'),
        ('Vos employeurs précédents ?', 'parcours'),
        ('Vous connaissez Docker ?', 'competences'),
        ('Combien coûte un POC ?', 'prestations'),
        ('Vous faites du RAG ?', 'projets'),
        ('Vous avez déjà construit un agent ?', 'projets'),
        ('Du LangGraph ?', 'projets'),
        ('Le projet sur les échecs ?', 'projets'),
    ]
    ecarts = []
    for q, attendu in attendus:
        hits = search(INDEX, q)
        obtenu = section_of(INDEX, hits[0][1]) if hits else 'RIEN'
        if obtenu != attendu:
            ecarts.append('« %s » -> %s au lieu de %s' % (q, obtenu, attendu))
    assert not ecarts, ' ; '.join(ecarts)


def test_legende_dit_la_verite():
    """La légende de la boîte annonce le rang et le nombre de documents. Elle
    était écrite en dur : le corpus est passé de 11 à 25 documents sans qu'elle
    bouge. Elle est désormais comparée à l'index à chaque exécution."""
    m = re.search(r'TF-IDF \+ SVD, rang (\d+), (\d+) documents', PAGE)
    assert m, 'la légende de la boîte « Interrogez le CV » est introuvable'
    rang, n = int(m.group(1)), int(m.group(2))
    assert rang == INDEX['k'], 'légende : rang %d, index : rang %d' % (rang, INDEX['k'])
    assert n == len(INDEX['docs']), (
        'légende : %d documents, index : %d' % (n, len(INDEX['docs'])))


def test_hors_sujet_ne_renvoie_rien():
    """Une question sans rapport doit tomber dans le repli honnête, pas inventer."""
    hits = search(INDEX, 'xylophone banane trampoline')
    assert not hits, 'une question hors sujet a trouvé %s' % (hits[0][1] if hits else None)


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    rates = 0
    for t in tests:
        try:
            t()
            print('  ok   %s' % t.__name__)
        except AssertionError as e:
            rates += 1
            print('  ECHEC %s : %s' % (t.__name__, e))
    print('%d/%d tests passent' % (len(tests) - rates, len(tests)))
    sys.exit(1 if rates else 0)
