# Tâche 2.2 - Développement du Module de Transcription Audio

## Objectif
Transcrire en texte les fichiers audio détectés (.mp3, .m4a…).

## Entrées
- Fichier audio provenant de `source_data/`.

## Sorties
- Fichier texte brut issu de la transcription.

## Sous-tâches
1. Installer la bibliothèque `openai-whisper` dans l'environnement virtuel.
2. Créer un module `transcriber.py` avec une fonction `transcribe(file_path)`.
3. Retourner le texte transcrit et l'enregistrer dans un dossier temporaire.
4. Prévoir le nettoyage des fichiers temporaires une fois la vectorisation terminée.

## Conseils d'implémentation
- Gérer les cas d'erreur si l'audio est de mauvaise qualité.
- Documenter la méthode d'appel dans le README.
