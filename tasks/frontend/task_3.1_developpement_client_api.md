# Tâche 3.1 - Développement du Client API

## Objectif
Communiquer avec le backend pour envoyer les messages utilisateur et recevoir les réponses.

## Entrées
- URL du backend disponible.

## Sorties
- Fichier `pegasus_api_client.dart` avec les méthodes de requête HTTP nécessaires.

## Sous-tâches
1. Créer `lib/api/pegasus_api_client.dart`.
2. Implémenter une méthode `Future<String> sendMessage(String message)` qui envoie une requête POST au `/chat` du backend.
3. Gérer l'authentification (token) dans les entêtes de la requête.
4. Traiter les erreurs réseau et retourner des messages d'erreur appropriés.

## Conseils d'implémentation
- Utiliser le package `http` ou `dio` selon les préférences du projet.
- Prévoir une variable `baseUrl` configurable via un fichier `.env` ou les constantes de l'app.
