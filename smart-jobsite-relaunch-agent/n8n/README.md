# n8n — workflow de relance hebdomadaire

## Ce que fait le workflow

`workflow.json` automatise le déclenchement hebdomadaire de l'agent :

1. **Schedule Trigger (lundi 8h)** — `cron: 0 8 * * 1`.
2. **Lire email simulé** — lit `/data/sample_report_email.txt` (email de démo listant 5 localités, format identique à un vrai email de chef de chantier).
3. **Construire la requête** — assemble le JSON attendu par l'API (`email_brut`, `date_du_jour`).
4. **Appeler l'agent (API)** — `POST http://localhost:8000/traiter-rapport-hebdomadaire`, qui invoque le graphe LangGraph une fois **par localité** mentionnée dans l'email (extraction, résolution de nom, calcul de cadence, classification, mise à jour de l'historique, génération de la section de rapport) et renvoie la liste des résultats. Avant le Jour 5, l'API (`/relancer`) ne traitait que la première localité d'un email même quand plusieurs étaient listées — corrigé lors de l'ajout des pages Streamlit, qui ont mis ce point en évidence.
5. **Préparer le fichier** — assemble les sections de rapport de toutes les localités traitées en un seul document Markdown.
6. **Écrire le rapport** — écrit `/out/rapport_hebdomadaire_<date>.md`.

## Comment le lancer

```bash
docker compose up --build
```

- API : http://localhost:8000/sante
- n8n (UI) : http://localhost:5678 — créer un compte propriétaire au premier lancement, puis importer `n8n/workflow.json` (Workflows → Import from File).
- Rapport généré : `./out/rapport_hebdomadaire_<date>.md`, lisible côté hôte.

## Point important — accès fichier n8n

Par défaut, n8n interdit aux nœuds de fichiers (`Read/Write File`) tout accès en dehors de `~/.n8n-files` (`SecurityConfig.restrictFileAccessTo`). Sans la variable d'environnement suivante, les nœuds « Lire email simulé » et « Écrire le rapport » échouent avec `Access to the file is not allowed.` :

```
N8N_RESTRICT_FILE_ACCESS_TO=/data;/out
```

Elle est déjà présente dans `docker-compose.yml`. Vérifié en conditions réelles (voir section suivante) : sans elle, l'exécution échoue systématiquement au nœud de lecture.

## Comment ça a été validé

Le bac à sable cloud utilisé pour construire cette démo bloque l'accès à Docker Hub (`docker pull` renvoie 403, y compris en configurant le proxy du démon Docker) — un blocage réseau de l'environnement, pas un problème de configuration. `docker-compose.yml` et `api/Dockerfile` sont donc livrés comme du code correct mais **non testé en conditions Docker dans cet environnement** ; à valider sur votre machine avec `docker compose up --build`.

Pour valider le workflow *réellement* (pas juste sa syntaxe), n8n a été installé via npm (`npm install -g n8n`, le registre npm n'étant pas bloqué) et exécuté directement contre l'API FastAPI locale. Le workflow a été importé, exécuté via l'API REST de n8n, et a produit avec succès `rapport_hebdomadaire_2026-09-07.md` avec les 5 localités de l'email de démo, chacune avec une seule anomalie d'écart d'inactivité (confirmant au passage que le correctif de l'accumulation d'`erreurs`, trouvé au Jour 4, tient aussi sur ce nouveau chemin multi-localités — cf. le résumé de reprise, section Jour 5). Le GIF de démo (`n8n_demo.gif`, à la racine du dépôt) a été capturé au Jour 4 sur la version single-locality du workflow (`/relancer`) ; le canevas visuel (6 nœuds, mêmes noms) est inchangé, seule la logique interne des nœuds Code et l'URL appelée ont changé au Jour 5 — non re-capturé, la démo visuelle reste représentative.

## Fichier d'entrée de démonstration

Le nœud « Lire email simulé » pointe vers `/data/sample_report_email.txt`, monté en lecture seule depuis `./data`. C'est un email fictif au format représentatif d'un vrai email de chef de chantier (cf. `docs/` pour le format).
