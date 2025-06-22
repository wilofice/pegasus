# Tâche 2.1 - Conception de l'Écran de Chat

## Objectif
Créer l'interface de conversation principale avec envoi de texte et micro.

## Entrées
- Projet Flutter avec les dépendances installées.

## Sorties
- Fichiers `chat_screen.dart`, `message_bubble.dart` et `message_composer.dart` opérationnels.

## Sous-tâches
1. Dans `lib/screens/`, créer `chat_screen.dart` contenant un `ListView` pour les messages.
2. Dans `lib/widgets/`, créer `message_bubble.dart` pour afficher un message (texte + style différent pour l'utilisateur et Pegasus).
3. Créer `message_composer.dart` avec un champ de saisie de texte et un bouton micro.
4. Prévoir un `ScrollController` pour garder la vue en bas lors de l'envoi d'un message.

## Conseils d'implémentation
- Utiliser les Widgets Material classiques pour une première version.
- Factoriser le code pour réutiliser `MessageBubble` dans d'autres écrans si besoin.
