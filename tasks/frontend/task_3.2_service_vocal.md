# Tâche 3.2 - Implémentation du Service Vocal

## Objectif
Permettre à l'utilisateur de parler à Pegasus et d'entendre la réponse.

## Entrées
- Dependances `speech_to_text` et `flutter_tts` (à ajouter si nécessaires).

## Sorties
- Fichier `voice_service.dart` gérant l'enregistrement vocal et la synthèse vocale.

## Sous-tâches
1. Ajouter les packages `speech_to_text` et `flutter_tts` dans `pubspec.yaml` si non présents.
2. Créer `lib/services/voice_service.dart` avec des méthodes pour démarrer/arrêter l'écoute et lire du texte.
3. Intégrer ces méthodes dans `message_composer.dart` (appui sur le bouton micro).
4. Tester le fonctionnement sur un appareil physique pour s'assurer des autorisations microphone.

## Conseils d'implémentation
- Gérer les permissions Android et iOS pour le micro et le haut-parleur.
- Prévoir une logique de fallback en cas d'indisponibilité du service vocal.
