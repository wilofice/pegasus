# Tâche 2.2 - Développement du Routeur de Webhook (`/webhook`)

## Objectif
Recevoir les notifications du data pipeline pour lancer l'analyse proactive.

## Entrées
- Requête HTTP POST envoyée par le pipeline contenant les informations du fichier traité.

## Sorties
- Accusé de réception ou message d'erreur.

## Sous-tâches
1. Créer `api/webhook_router.py` et définir la route POST `/webhook`.
2. Valider la signature ou le token envoyé par le pipeline.
3. Transmettre les données reçues au moteur proactif.
4. Retourner un message de confirmation.

## Conseils d'implémentation
- Limiter l'accès à cette route au seul pipeline (IP whitelist ou token secret).
- Journaliser les notifications reçues pour audit.
