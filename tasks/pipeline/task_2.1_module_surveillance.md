# Tâche 2.1 - Développement du Module de Surveillance

## Objectif
Détecter automatiquement tout nouveau fichier déposé dans `source_data/`.

## Entrées
- Dossier `source_data/` surveillé.

## Sorties
- Script Python capable de lancer des actions lorsque de nouveaux fichiers sont présents.

## Sous-tâches
1. Installer la bibliothèque `watchdog` dans l'environnement virtuel.
2. Créer un module `watcher.py` qui observe `source_data/`.
3. Définir un gestionnaire d'événements qui déclenche le traitement du fichier.
4. Prévoir la journalisation des événements dans `logs/pipeline.log`.

## Conseils d'implémentation
- Tester la détection de fichiers en copiant manuellement des exemples.
- Organiser le code pour pouvoir ajouter facilement d'autres types d'événements.
