# Tâche 1.3 - Mise en Place de l'Environnement Virtuel

## Objectif
Créer un environnement virtuel Python et installer les dépendances du pipeline.

## Entrées
- Dossier `data_pipeline/` créé lors de la tâche 1.2.
- Fichier `requirements.txt` listant les dépendances.

## Sorties
- Environnement virtuel opérationnel dans `data_pipeline/venv/`.
- Packages Python installés.

## Sous-tâches
1. Se placer dans `data_pipeline/`.
2. Créer l'environnement virtuel avec `python -m venv venv`.
3. Activer l'environnement virtuel (`source venv/bin/activate`).
4. Installer les dépendances avec `pip install -r requirements.txt`.
5. Ajouter un rappel dans le README sur l'activation de l'environnement.

## Conseils d'implémentation
- S'assurer que la version de Python correspond à celle installée en 1.1.
- Garder le fichier `requirements.txt` minimal au démarrage.
