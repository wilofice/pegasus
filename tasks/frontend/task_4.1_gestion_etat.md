# Tâche 4.1 - Mise en Place de la Gestion d'État

## Objectif
Gérer de manière efficace la liste des messages et les données partagées dans l'application.

## Entrées
- Widgets et services créés précédemment.

## Sorties
- Fichier `chat_provider.dart` (ou équivalent) implémentant la logique d'état.

## Sous-tâches
1. Dans `lib/providers/`, créer `chat_provider.dart` utilisant `Riverpod` ou `Provider`.
2. Stocker la liste des messages et exposer des méthodes pour en ajouter ou nettoyer.
3. Notifier l'UI lors des changements d'état afin que `chat_screen.dart` se mette à jour automatiquement.
4. Ajouter des tests unitaires simples pour vérifier le fonctionnement du provider.

## Conseils d'implémentation
- Séparer le modèle de message dans `models/message_model.dart` pour plus de clarté.
- Utiliser des `StateNotifier` ou `ChangeNotifier` selon la solution choisie.
