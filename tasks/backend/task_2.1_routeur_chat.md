# Tâche 2.1 - Développement du Routeur de Chat (`/chat`)

## Objectif
Gérer la réception des messages utilisateurs depuis le frontend.

## Entrées
- Requête HTTP POST contenant un message et un token d'authentification.

## Sorties
- Réponse JSON avec la réponse générée par Pegasus.

## Sous-tâches
1. Dans `api/chat_router.py`, définir une route POST `/chat`.
2. Valider l'authentification (ex: header `Authorization`).
3. Appeler l'orchestrateur pour traiter le message et récupérer la réponse.
4. Retourner la réponse au format JSON.

## Conseils d'implémentation
- Utiliser les modèles Pydantic pour définir le schéma de la requête et de la réponse.
- Prévoir des tests unitaires pour ce routeur à l'aide de `TestClient` de FastAPI.
