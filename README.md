# Portfolio - Clément Reboul, AI Engineer freelance

Portfolio personnel et professionnel : du notebook à la production (Machine Learning, MLOps, GenAI/RAG).
Sert aussi de support commercial : la section **Prestations** liste des missions freelance cadrées (périmètre, durée).

**En ligne :** https://clementrbl.github.io/portfolio/

## Contenu

| Page | Description |
|---|---|
| `index.html` | Portfolio : profil, compétences, projets, projet phare, **prestations**, réflexivité, contact |
| `rapport.html` | Rapport de conduite de projet Data (industrialisation d'un modèle de scoring crédit, MLOps) |
| `carte-mentale.html` | Carte mentale interactive des compétences |
| `assets/` | Captures des projets, CV PDF, image de partage Open Graph |
| `assets/search-index.json` | Index de recherche vectorielle de la palette (généré) |
| `tools/build_index.py` | Génère l'index : TF-IDF + SVD tronquée sur `tools/corpus.json` |
| `tools/build_images.py` | Fabrique les médias d'`assets/` d'après `tools/images.json` |
| `sitemap.xml` | Plan de site (à déclarer dans Google Search Console) |

## Lancer en local

Le site est **statique, sans build ni dépendance**. Deux façons de le tester :

### Option 1 - Serveur local (recommandé, reproduit GitHub Pages)

Depuis le dossier du dépôt :

```bash
python3 -m http.server 8000
```

Puis ouvrir **http://localhost:8000/** dans le navigateur.
(Alternative Node : `npx serve` - ou l'extension **Live Server** de VS Code, clic droit sur `index.html` → *Open with Live Server*.)

> Astuce : après une modif, recharge avec **Ctrl+Shift+R** (Cmd+Shift+R sur Mac) pour ignorer le cache.

### Option 2 - Ouvrir directement le fichier

Double-cliquer sur `index.html` (ouverture en `file://`). Fonctionne pour l'essentiel ; le serveur local reste préférable pour reproduire fidèlement le comportement en ligne.

## Le portfolio calcule

Deux éléments ne sont pas des maquettes :

**L'API de scoring en production.** Le panneau du hero et la démo de l'étude de
cas appellent réellement `POST /predict` sur le Space Hugging Face. La latence
affichée est l'aller-retour mesuré dans le navigateur. Si le Space dort, l'état
passe à « API en veille » et les réponses viennent d'un jeu relevé à l'avance - dit explicitement.

**La recherche vectorielle.** `tools/build_index.py` construit hors ligne un
espace latent (TF-IDF puis SVD tronquée, rang 14) sur le contenu du site ; le
navigateur y projette la requête et classe les documents par similarité
cosinus. Taper « comment tu surveilles un modèle en prod » remonte l'étude de
cas sans qu'aucun de ses mots n'ait été saisi.

**Rien n'est généré.** Chaque document porte une réponse écrite à la main,
servie telle quelle. La recherche est vectorielle, la réponse ne l'est pas :
aucun modèle n'écrit de phrase, donc aucune phrase ne peut être inventée.

Le corpus mêle deux sortes de documents. Onze correspondent aux sections du
site. Les autres sont thématiques - « rag », « agents », « tarifs »,
« formation » - et portent un champ `section` qui dit où envoyer le visiteur.
Ils existent parce qu'une question précise mérite une réponse précise :
« Vous faites du RAG ? » ne doit pas renvoyer le résumé des dix projets.
Seuls les documents de section alimentent le rail sémantique et la carte
latente du hero.

Regénérer l'index après avoir modifié `tools/corpus.json` :

```bash
python3 tools/build_index.py   # numpy requis
python3 tools/test_search.py   # 9 tests de régression, sans rien installer
```

Les tests vérifient deux choses différentes : qu'une reformulation mène à la
bonne **section** (exigence forte, 92 % minimum) et qu'elle trouve le bon
**document** (mesure de finesse, 72 % minimum). Ils lisent les questions
proposées et la légende affichée directement dans `index.html` : ajouter une
question sans réponse, ou laisser la légende annoncer un rang qui n'est plus
le bon, casse un test.

## Les images et la vidéo

Chaque capture vient d'un livrable réel : une figure de notebook, une capture
d'interface, une sortie de pipeline. `tools/images.json` note, pour chacune, le
projet et la figure d'origine, le cadrage et la taille produite ;
`tools/build_images.py` applique la recette. Rien n'est dessiné pour le site.

Une capture peut aussi venir d'une application qu'il faut faire tourner : celle
de l'agent d'ouvertures FFE a été prise sur la pile lancée en local, puis
déposée dans `docs/captures/` du projet, d'où le manifeste la reprend.

Les vignettes de projet sont toutes produites en 1200x500, le rapport que la
feuille de style impose aux couvertures : le cadrage est donc décidé à la
fabrication, jamais laissé au navigateur, et reste le même à toutes les
largeurs d'écran.

La carte Astro Dynamics porte deux vues : la courbe d'entraînement et
l'atterrissage filmé. La vidéo dure 22 secondes, pèse 50 Ko, n'a pas de piste
son et ne se télécharge qu'au moment où l'on demande à la voir.

```bash
# ImageMagick et ffmpeg requis ; Plotly seulement pour les figures en JSON
uv run --with plotly --with kaleido python3 tools/build_images.py
```

Les sources vivent dans les dépôts des projets, hors de celui-ci : le script ne
tourne donc que sur une machine qui les héberge, et signale celles qu'il ne
trouve pas au lieu de s'arrêter.

## Les trois pages ne font qu'un site

Le rapport et la carte mentale lisent le mode et le thème choisis sur le
portfolio (`fxMode`, `theme`) et appliquent les mêmes palettes, aux mêmes
valeurs : Game sombre, Standard sombre, Standard clair. Comme sur le
portfolio, le mode Game n'existe qu'en sombre - le bouton de thème y reste
visible mais inerte, et dit pourquoi. La préférence enregistrée n'est pas
touchée : elle se retrouve intacte au retour en mode Standard.

## Sécurité

Les en-têtes réels sont posés par une fonction Edge Netlify sur
`clement-reboul.fr/portfolio/*` : `frame-ancestors`, `X-Frame-Options`,
`Referrer-Policy`, `Permissions-Policy`. Chaque page porte en plus une balise
`Content-Security-Policy` reprenant la même politique, parce que l'origine
`clementrbl.github.io` est servie sans aucun en-tête. Seul `frame-ancestors`
manque à la balise : une meta ne peut pas le porter.

La carte mentale charge d3 et markmap depuis jsDeliver. Les quatre ressources
sont épinglées par empreinte SHA-384 (`integrity` + `crossorigin`) : une
réponse modifiée en chemin est refusée par le navigateur au lieu d'être
exécutée sur le domaine.

Rien n'est injecté : les seules écritures de balisage portent sur des chaînes
écrites en dur, et tout ce qui vient d'ailleurs - la question posée au CV, la
réponse de l'API - passe par `textContent` ou est échappé.

## Déploiement

Poussé sur la branche `main` → **GitHub Pages** publie automatiquement à chaque push (le fichier `.nojekyll` désactive le traitement Jekyll et sert les fichiers tels quels).

## Projet technique mis en avant

**Credit Scoring MLOps** - mise en production d'un modèle de scoring crédit :
API FastAPI conteneurisée, CI/CD (GitHub Actions → Hugging Face Spaces), monitoring de drift (Evidently) et dashboard.

- Code : https://github.com/clementRbl/credit-scoring-mlops
- API en ligne : https://clementrbl-credit-scoring-api.hf.space/docs

## Technique

Site statique : HTML/CSS + JavaScript vanilla, **aucune dépendance**.
Thème clair/sombre, responsive, accessible (navigation clavier, contenu visible sans JavaScript, textes alternatifs).

### Deux directions artistiques

Le site se charge en mode **Standard** : palette froide, angles droits, surfaces
propres - registre instrument de mesure. La navigation y passe par une **palette
de commandes** (`⌘K` / `Ctrl K`, ou `M`).

Le mode Standard a ses propres animations, toutes adossées à une donnée réelle
du projet : flux d'inférence qui s'écrit jeton par jeton dans le panneau de
statut, sparkline de latence, compteurs de métriques, jeton qui parcourt le
pipeline MLOps, graphe latent en fond de hero, barre de progression de lecture.
Toutes se désactivent sous `prefers-reduced-motion`.

Le mode **Game** (DA « survivant » : ambre, coins biseautés, grain, braises,
curseur torche, roue de sélection) s'active depuis la palette et se retient dans
le `localStorage`. Basculer de mode recharge la page : les effets du mode Game
s'initialisent une seule fois par chargement.
