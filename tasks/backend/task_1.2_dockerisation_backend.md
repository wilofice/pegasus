# Tâche 1.2 - Dockerisation du Backend

## Objectif
Emballer l'application FastAPI dans un conteneur pour faciliter le déploiement.

## Entrées
- Squelette FastAPI issu de la tâche 1.1.

## Sorties
- `Dockerfile` et instructions pour lancer l'image.

## Sous-tâches
1. Créer un `Dockerfile` installant les dépendances et lançant `uvicorn`.
2. Ajouter un fichier `.dockerignore` pour exclure `__pycache__` et l'environnement virtuel.
3. Documenter les commandes `docker build` et `docker run` dans `README.md`.
4. Tester la construction de l'image en local.

## Conseils d'implémentation
- Utiliser une image de base Python officielle (ex: `python:3.11-slim`).
- Prévoir le paramétrage du port d'écoute via une variable d'environnement.
