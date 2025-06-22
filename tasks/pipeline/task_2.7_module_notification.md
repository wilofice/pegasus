# Tâche 2.7 - Développement du Module de Notification

## Objectif
Informer le backend lorsque le traitement d'un fichier est terminé.

## Entrées
- Résultat d'une étape de traitement réussie (fichier vectorisé).

## Sorties
- Envoi d'une requête HTTP POST au backend avec les informations du fichier traité.

## Sous-tâches
1. Ajouter la dépendance `requests` si elle n'est pas déjà présente.
2. Écrire une fonction `send_webhook(data)` dans `notifier.py` qui poste sur l'URL configurée du backend.
3. Gérer les erreurs réseau et consigner les échecs dans le log.
4. Appeler cette fonction après la mise à jour de la base de données.

## Conseils d'implémentation
- Utiliser les variables d'environnement pour stocker l'URL du backend et le token éventuel.
- Prévoir une stratégie de retry en cas d'échec temporaire.
