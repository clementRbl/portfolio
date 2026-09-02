#!/usr/bin/env python3
"""Construit l'index de recherche vectorielle de la palette de commandes.

Analyse latente (LSA) : TF-IDF sur les sections du portfolio, puis SVD tronquée.
Le corpus fait une quinzaine de documents, donc le rang utile est faible - on
garde 12 composantes. Sortie : assets/search-index.json, lu par index.html.

    python3 tools/build_index.py

Le fichier contient le vocabulaire, l'IDF, la projection des termes dans
l'espace latent et la position de chaque document. Les mêmes vecteurs servent
à placer les projets dans le graphe latent du hero.
"""
import json, math, re, sys, unicodedata
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
K = 12                      # composantes latentes (rang du corpus ~15)
MAX_TERMS = 460             # vocabulaire retenu, par IDF décroissant

# Suffixes français les plus courants : racinisation légère, sans dépendance.
# Les terminaisons de conjugaison comptent autant que celles de dérivation : le
# site vouvoie, donc un visiteur écrit « vous travaillez » là où le corpus dit
# « tu travailles ». Sans -ez et -e, ces deux formes tombent dans deux
# entrées de vocabulaire différentes et la question ne trouve rien. Rangés du
# plus long au plus court : la première correspondance gagne, en une seule passe.
# -ons est volontairement absent : il découperait « missions » en « missi » alors
# que « mission » resterait entier, et casserait tous les pluriels en -on.
SUFFIXES = ('issements', 'issement', 'ations', 'ation', 'ements', 'ement', 'ateurs',
            'ateur', 'trices', 'trice', 'ances', 'ance', 'ences', 'ence', 'ismes',
            'isme', 'istes', 'iste', 'ités', 'ité', 'eurs', 'euse', 'eur', 'ives',
            'ive', 'ifs', 'if', 'aux', 'ales', 'ale', 'els', 'elle', 'és', 'ées',
            'ée', 'ez', 'er', 'es', 'e', 's')

STOP = set("""a au aux avec ce ces dans de des du elle en et eux il ils je la le les leur
lui ma mais me meme mes moi mon ne nos notre nous on ou par pas pour qu que qui sa se ses
son sur ta te tes toi ton tu un une vos votre vous c d j l m n s t y ete etee etees etes
etant suis es est sommes etes sont sera seront etais etait avoir eu ai as avons avez ont
plus tres tout tous toute toutes autre autres apres avant entre sans sous chez donc alors
si comme quand aussi bien fait faire cela ceci celui ceux la les des aux""".split())


def strip_accents(t):
    return ''.join(c for c in unicodedata.normalize('NFD', t)
                   if unicodedata.category(c) != 'Mn')


# Réécritures appliquées APRÈS la coupe du suffixe. Le français alterne y et i
# selon la personne : déployer / déploie, employer / emploie. Sans cette règle,
# le mot le plus central du portfolio se scinde en deux entrées de vocabulaire,
# « deploy » et « deploi », et son poids est divisé par deux. Exporté dans le
# JSON comme les autres tables : le navigateur applique la même chose.
REWRITES = (('y', 'i'),)


def stem(w):
    for suf in SUFFIXES:
        if len(w) > len(suf) + 3 and w.endswith(suf):
            w = w[:-len(suf)]
            break
    for a, b in REWRITES:
        if len(w) > 3 and w.endswith(a):
            return w[:-len(a)] + b
    return w


def tokenize(text):
    text = strip_accents(text.lower())
    words = re.findall(r"[a-z0-9][a-z0-9+#.\-]{1,}", text)
    out = []
    for w in words:
        w = w.strip('.-')
        if len(w) < 2 or w in STOP or w.isdigit():
            continue
        out.append(stem(w))
    return out


def build(docs):
    """docs : liste de (id, titre, texte). Renvoie le dictionnaire d'index."""
    toks = [tokenize(t) for _, _, t in docs]
    N = len(docs)
    df = {}
    for tk in toks:
        for w in set(tk):
            df[w] = df.get(w, 0) + 1
    # On écarte les termes présents partout (aucun pouvoir discriminant)
    cand = [(w, math.log((1 + N) / (1 + c)) + 1.0) for w, c in df.items() if c < N]
    cand.sort(key=lambda x: (-x[1], x[0]))
    vocab = [w for w, _ in cand[:MAX_TERMS]]
    idf = {w: i for w, i in cand[:MAX_TERMS]}
    vi = {w: i for i, w in enumerate(vocab)}

    X = np.zeros((N, len(vocab)), dtype=np.float64)
    for d, tk in enumerate(toks):
        for w in tk:
            if w in vi:
                X[d, vi[w]] += 1.0
    X = np.log1p(X)
    for w, i in vi.items():
        X[:, i] *= idf[w]
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    X /= np.where(norms == 0, 1, norms)

    k = min(K, min(X.shape) - 1)
    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    Uk, Sk, Vk = U[:, :k], S[:k], Vt[:k, :]

    doc_vecs = Uk * Sk                       # documents dans l'espace latent
    term_vecs = (Vk.T * Sk)                  # termes, même espace : une requête
                                             # est la somme de ses termes

    def unit(M):
        n = np.linalg.norm(M, axis=1, keepdims=True)
        return M / np.where(n == 0, 1, n)

    # Projection 2D des documents, pour le graphe latent du hero : ACP sur les
    # vecteurs latents, en écartant la 1re composante (direction moyenne, non
    # discriminante) au profit des suivantes, qui portent la structure.
    Z = doc_vecs - doc_vecs.mean(axis=0)
    _, _, Vz = np.linalg.svd(Z, full_matrices=False)
    xy = Z @ Vz[:2].T
    xy /= np.abs(xy).max(axis=0)

    return {
        'k': int(k),
        # Exportés pour que le JS applique EXACTEMENT la même normalisation.
        # Les dupliquer côté navigateur, c'est se garantir une dérive silencieuse.
        'stop': sorted(STOP),
        'suffixes': list(SUFFIXES),
        'rewrites': [list(r) for r in REWRITES],
        'vocab': vocab,
        'idf': [round(idf[w], 4) for w in vocab],
        'terms': [[round(float(v), 4) for v in row] for row in term_vecs],
        'docs': [{'id': docs[i][0], 'title': docs[i][1],
                  'xy': [round(float(xy[i][0]), 4), round(float(xy[i][1]), 4)],
                  'v': [round(float(v), 4) for v in row]}
                 for i, row in enumerate(unit(doc_vecs))],
    }



# ---------------------------------------------------------------------------
# Interrogation de l'index construit. Reproduit vecSearch() de index.html, et
# s'appuie sur les tables exportées dans le JSON plutôt que sur les constantes
# du module : c'est exactement ce que fait le navigateur, donc un écart entre
# les deux se voit ici au lieu de se voir en production.
# ---------------------------------------------------------------------------

def load_index(path=None):
    path = path or (ROOT / 'assets' / 'search-index.json')
    return json.loads(path.read_text(encoding='utf-8'))


def query_tokens(index, query):
    """Racines retenues d'une requête, dans l'ordre, avec leur présence au vocabulaire."""
    stop = set(index['stop'])
    suffixes = tuple(index['suffixes'])
    vocab = set(index['vocab'])

    rewrites = index.get('rewrites', [])

    def stem_q(w):
        for suf in suffixes:
            if len(w) > len(suf) + 3 and w.endswith(suf):
                w = w[:-len(suf)]
                break
        for a, b in rewrites:
            if len(w) > 3 and w.endswith(a):
                return w[:-len(a)] + b
        return w

    out = []
    for w in re.findall(r"[a-z0-9][a-z0-9+#.\-]{1,}", strip_accents(query.lower())):
        w = w.strip('.-')
        if len(w) < 2 or w in stop or w.isdigit():
            continue
        root = stem_q(w)
        out.append((root, root in vocab))
    return out


def search(index, query, min_score=0.0, limit=3):
    """Renvoie [(score, id, titre)] trié, ou [] si aucun terme n'est au vocabulaire."""
    pos = {w: i for i, w in enumerate(index['vocab'])}
    k = index['k']
    v = [0.0] * k
    used = 0
    for root, known in query_tokens(index, query):
        if not known:
            continue
        used += 1
        row, w = index['terms'][pos[root]], index['idf'][pos[root]]
        for d in range(k):
            v[d] += row[d] * w
    if not used:
        return []
    n = math.sqrt(sum(x * x for x in v))
    if not n:
        return []
    v = [x / n for x in v]
    hits = [(sum(doc['v'][c] * v[c] for c in range(k)), doc['id'], doc['title'])
            for doc in index['docs']]
    hits.sort(reverse=True)
    return [h for h in hits if h[0] >= min_score][:limit]


if __name__ == '__main__':
    corpus = json.loads((ROOT / 'tools' / 'corpus.json').read_text(encoding='utf-8'))
    docs = [(d['id'], d['title'], ' '.join([d['title'], d.get('text', ''),
                                            ' '.join(d.get('queries', []))]))
            for d in corpus]
    index = build(docs)
    # Réponse rédigée à la main, servie telle quelle par la boîte « Interrogez
    # mon CV » : la recherche est vectorielle, la réponse ne l'est pas. Rien
    # n'est généré à la volée, donc rien ne peut être inventé.
    for i, d in enumerate(corpus):
        index['docs'][i]['a'] = d.get('answer', '')
    index['generated'] = 'tools/build_index.py - LSA rang %d sur %d documents' % (index['k'], len(docs))
    out = ROOT / 'assets' / 'search-index.json'
    out.write_text(json.dumps(index, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print('%s - %d documents, %d termes, rang %d, %.1f Ko'
          % (out.name, len(docs), len(index['vocab']), index['k'], out.stat().st_size / 1024))
