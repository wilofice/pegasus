# Tâche 3.3 - Implémentation de l'Orchestrateur (Mode Réactif)

## Objectif
Combiner le contexte issu de la base vectorielle avec la requête utilisateur pour interroger le LLM.

## Entrées
- Texte du message utilisateur.
- Accès au `VectorDBClient` et au `LLMClient`.

## Sorties
- Réponse générée par le LLM avec le contexte approprié.

## Sous-tâches
1. Créer `core/orchestrator.py` avec une fonction principale `handle_chat(message)`.
2. Transformer le message en embedding et interroger la base vectorielle via `VectorDBClient` pour récupérer le contexte pertinent.
3. Construire le prompt complet en intégrant le contexte et le message.
4. Appeler `LLMClient.generate()` et retourner la réponse.

## Conseils d'implémentation
- Limiter la taille du contexte ajouté pour rester sous la limite de tokens du modèle.
- Prévoir des logs détaillés pour suivre les requêtes utilisateur.
