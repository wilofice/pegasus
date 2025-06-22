# Tâche 4.1 - Assemblage des Composants

## Objectif
Relier les routeurs API à la logique métier et gérer la configuration de manière sécurisée.

## Entrées
- Routeurs `chat_router` et `webhook_router`.
- Clients `VectorDBClient` et `LLMClient`.

## Sorties
- Application FastAPI prête à être exécutée en production.

## Sous-tâches
1. Importer les routeurs dans `main.py` et les inclure dans l'application.
2. Charger la configuration (clés API, chemins) via `config.py` ou variables d'environnement.
3. Initialiser les clients de service et les passer aux routeurs via `Depends` ou injection manuelle.
4. Vérifier que l'application démarre sans erreur et que les endpoints répondent.

## Conseils d'implémentation
- Séparer clairement le code de configuration pour faciliter le déploiement dans différents environnements.
- Ajouter un fichier `.env.example` listant les variables nécessaires.
