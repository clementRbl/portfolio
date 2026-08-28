# Portfolio — Clément Reboul, AI Engineer freelance

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
| `sitemap.xml` | Plan de site (à déclarer dans Google Search Console) |

## Lancer en local

Le site est **statique, sans build ni dépendance**. Deux façons de le tester :

### Option 1 — Serveur local (recommandé, reproduit GitHub Pages)

Depuis le dossier du dépôt :

```bash
python3 -m http.server 8000
```

Puis ouvrir **http://localhost:8000/** dans le navigateur.
(Alternative Node : `npx serve` — ou l'extension **Live Server** de VS Code, clic droit sur `index.html` → *Open with Live Server*.)

> Astuce : après une modif, recharge avec **Ctrl+Shift+R** (Cmd+Shift+R sur Mac) pour ignorer le cache.

### Option 2 — Ouvrir directement le fichier

Double-cliquer sur `index.html` (ouverture en `file://`). Fonctionne pour l'essentiel ; le serveur local reste préférable pour reproduire fidèlement le comportement en ligne.

## Déploiement

Poussé sur la branche `main` → **GitHub Pages** publie automatiquement à chaque push (le fichier `.nojekyll` désactive le traitement Jekyll et sert les fichiers tels quels).

## Projet technique mis en avant

**Credit Scoring MLOps** — mise en production d'un modèle de scoring crédit :
API FastAPI conteneurisée, CI/CD (GitHub Actions → Hugging Face Spaces), monitoring de drift (Evidently) et dashboard.

- Code : https://github.com/clementRbl/credit-scoring-mlops
- API en ligne : https://clementrbl-credit-scoring-api.hf.space/docs

## Technique

Site statique : HTML/CSS + JavaScript vanilla, **aucune dépendance**.
Thème clair/sombre, responsive, accessible (navigation clavier, contenu visible sans JavaScript, textes alternatifs).

### Deux directions artistiques

Le site se charge en mode **Standard** : palette froide, angles droits, surfaces
propres — registre instrument de mesure. La navigation y passe par une **palette
de commandes** (`⌘K` / `Ctrl K`, ou `M`).

Le mode **Game** (DA « survivant » : ambre, coins biseautés, grain, braises,
curseur torche, roue de sélection) s'active depuis la palette et se retient dans
le `localStorage`. Basculer de mode recharge la page : les effets du mode Game
s'initialisent une seule fois par chargement.
