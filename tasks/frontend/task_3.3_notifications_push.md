# Tâche 3.3 - Configuration des Notifications Push

## Objectif
Recevoir les messages proactifs envoyés par le backend via Firebase Cloud Messaging (FCM).

## Entrées
- Projet Firebase configuré.
- Clé de messagerie FCM.

## Sorties
- Fichier `notification_service.dart` permettant de recevoir et afficher les notifications.

## Sous-tâches
1. Ajouter et configurer `firebase_messaging` dans `pubspec.yaml`.
2. Suivre la documentation Firebase pour enregistrer l'application (Android et iOS).
3. Implémenter `notification_service.dart` avec l'initialisation FCM et la gestion des notifications en arrière-plan.
4. Tester la réception d'une notification en envoyant un message depuis la console Firebase ou un script backend.

## Conseils d'implémentation
- Vérifier les fichiers `AndroidManifest.xml` et `Info.plist` pour les permissions nécessaires.
- Prévoir un canal de notification spécifique à Pegasus pour une meilleure organisation.
