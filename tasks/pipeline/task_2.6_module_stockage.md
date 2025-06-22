# Tâche 2.6 - Développement du Module de Stockage

## Objectif
Enregistrer les embeddings et métadonnées dans une base ChromaDB locale.

## Entrées
- Vecteurs calculés et informations sur les textes originaux.

## Sorties
- Base de données ChromaDB dans `database/` mise à jour.

## Sous-tâches
1. Installer `chromadb` et configurer la base locale dans `database/`.
2. Créer un module `storage.py` permettant d'insérer un vecteur et ses métadonnées.
3. Prévoir une méthode pour interroger la base par la suite.
4. Mettre à jour les logs à chaque insertion réussie.

## Conseils d'implémentation
- Organiser le schéma de stockage pour retrouver facilement l'origine de chaque chunk.
- Tester avec de petites données avant de traiter de gros fichiers.
