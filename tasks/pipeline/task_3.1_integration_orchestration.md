# Tâche 3.1 - Intégration et Orchestration

## Objectif
Assembler tous les modules du pipeline pour un fonctionnement continu et robuste.

## Entrées
- Modules développés lors des tâches 2.x.

## Sorties
- Script `pipeline.py` complet orchestrant l'ensemble des traitements.

## Sous-tâches
1. Importer les modules `watcher`, `transcriber`, `text_extractor`, `segmenter`, `vectorizer`, `storage`, `notifier`.
2. Mettre en place un flux de traitement séquentiel : détection > transcription/extraction > segmentation > vectorisation > stockage > notification.
3. Gérer les erreurs à chaque étape et écrire des messages détaillés dans `logs/pipeline.log`.
4. Fournir une interface ligne de commande pour lancer ou arrêter le pipeline.

## Conseils d'implémentation
- Utiliser un `try/except` global pour éviter que le pipeline ne s'arrête brutalement.
- Prévoir une option de démarrage en mode "dry-run" pour tester sans écrire dans la base.
