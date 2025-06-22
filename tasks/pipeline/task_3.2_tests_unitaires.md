# Tâche 3.2 - Tests Unitaires du Data Pipeline

## Objectif
Valider le bon fonctionnement de chaque module avec les fichiers de test fournis.

## Entrées
- Fichiers d'exemple : `journal_intime_22-06-2025.mp3`, `export_whatsapp_famille.txt`, `email_confirmation_vol_italie.eml`.
- Modules développés dans les tâches précédentes.

## Sorties
- Rapport de tests indiquant la réussite ou l'échec de chaque étape.

## Sous-tâches
1. Préparer un dossier `tests/` contenant les fichiers d'exemple.
2. Écrire un script de tests (ex. avec `pytest`) couvrant la transcription, l'extraction, la segmentation et la vectorisation.
3. Vérifier que les données sont correctement stockées dans ChromaDB après traitement.
4. Documenter la procédure d'exécution des tests dans le README.

## Conseils d'implémentation
- Utiliser des fixtures pour isoler les tests et nettoyer la base après coup.
- Prévoir un jeu de données minimal pour accélérer les tests.
