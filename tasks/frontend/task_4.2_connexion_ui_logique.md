# Tâche 4.2 - Connexion UI et Logique

## Objectif
Relier l'interface utilisateur aux services afin de créer un flux de conversation complet.

## Entrées
- Client API, services vocaux et provider d'état configurés.

## Sorties
- Écran de chat fonctionnel communiquant avec le backend.

## Sous-tâches
1. Appeler `PegasusApiClient.sendMessage` lorsque l'utilisateur envoie un message ou termine une dictée vocale.
2. Ajouter le message utilisateur et la réponse de Pegasus dans le provider d'état pour rafraîchir l'UI.
3. Activer la synthèse vocale via `VoiceService` lorsque Pegasus répond.
4. Gérer les erreurs (perte de connexion, token invalide) et informer l'utilisateur.

## Conseils d'implémentation
- Veiller à la gestion asynchrone pour éviter de bloquer l'interface pendant les appels réseau.
- Tester la fonctionnalité sur émulateur et appareil réel pour s'assurer du bon enchaînement des actions.
