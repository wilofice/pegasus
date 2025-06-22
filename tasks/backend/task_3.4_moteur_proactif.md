# Tâche 3.4 - Implémentation du Moteur Proactif

## Objectif
Analyser automatiquement les nouvelles données pour initier des conversations pertinentes.

## Entrées
- Notification reçue via `/webhook` contenant les données nouvellement stockées.

## Sorties
- Messages envoyés à l'utilisateur si un sujet intéressant est détecté.

## Sous-tâches
1. Créer `core/proactive_engine.py` avec une fonction `process_notification(payload)`.
2. Utiliser `VectorDBClient` pour récupérer les passages associés aux nouvelles données.
3. Formuler un prompt résumant ces passages et appeler `LLMClient.generate()` pour déterminer s'il faut contacter l'utilisateur.
4. Si nécessaire, envoyer la réponse via un canal de notification (ex: push vers le frontend).

## Conseils d'implémentation
- Prévoir un système de seuil ou de règles pour éviter trop de notifications.
- Journaliser toutes les décisions prises par le moteur proactif.
