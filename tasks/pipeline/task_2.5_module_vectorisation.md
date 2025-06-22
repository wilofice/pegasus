# Tâche 2.5 - Développement du Module de Vectorisation

## Objectif
Convertir chaque segment de texte en vecteur numérique.

## Entrées
- Liste de textes segmentés.

## Sorties
- Vecteurs d'embedding correspondants.

## Sous-tâches
1. Installer la bibliothèque `sentence-transformers` dans l'environnement virtuel.
2. Créer un module `vectorizer.py` avec une fonction `embed(chunks)`.
3. Utiliser un modèle pré-entraîné (par ex. `all-MiniLM-L6-v2`).
4. Retourner la liste des vecteurs et conserver les indices d'origine.

## Conseils d'implémentation
- Charger le modèle une seule fois au démarrage du pipeline.
- Évaluer la taille mémoire occupée et ajuster le batch size si nécessaire.
