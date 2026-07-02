# Portfolio — Clément Reboul, AI Engineer

Portfolio personnel et professionnel : du notebook à la production (Machine Learning, MLOps, GenAI/RAG).

**En ligne :** https://clementrbl.github.io/portfolio/

## Contenu

| Page | Description |
|---|---|
| `index.html` | Portfolio : profil, compétences, projets, projet phare, réflexivité, contact |
| `rapport.html` | Rapport de conduite de projet Data (industrialisation d'un modèle de scoring crédit, MLOps) |
| `carte-mentale.html` | Carte mentale interactive des compétences |
| `assets/` | Captures des projets |

## Projet technique mis en avant

**Credit Scoring MLOps** — mise en production d'un modèle de scoring crédit :
API FastAPI conteneurisée, CI/CD (GitHub Actions → Hugging Face Spaces), monitoring de drift (Evidently) et dashboard.

- Code : https://github.com/clementRbl/credit-scoring-mlops
- API en ligne : https://clementrbl-credit-scoring-api.hf.space/docs

## Technique

Site statique, sans dépendance ni build : HTML/CSS + JavaScript vanilla.
Thème clair/sombre, responsive, accessible (navigation clavier, contenu visible sans JavaScript, textes alternatifs).

Servi tel quel par GitHub Pages (le fichier `.nojekyll` désactive le traitement Jekyll).
