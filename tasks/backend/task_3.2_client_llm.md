# Tâche 3.2 - Création du Client pour le LLM

## Objectif
Envoyer des prompts à un service LLM externe (OpenAI ou Anthropic) et récupérer les réponses.

## Entrées
- Clé API du fournisseur de LLM.
- Texte du prompt à envoyer.

## Sorties
- Réponse textuelle générée par le modèle.

## Sous-tâches
1. Créer `services/llm_client.py` avec une classe `LLMClient`.
2. Implémenter une méthode `generate(prompt)` qui fait l'appel HTTP au LLM.
3. Stocker la clé API de manière sécurisée (variable d'environnement ou fichier `.env`).
4. Gérer les erreurs réseau et les limitations de quota.

## Conseils d'implémentation
- Prévoir la possibilité de changer de fournisseur de LLM facilement (pattern stratégie).
- Ajouter un mode "mock" pour les tests sans appel réseau.
