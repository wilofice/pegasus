# Tâche 3.1 - Création du Client pour la Base Vectorielle

## Objectif
Permettre au backend d'interroger la base ChromaDB créée par le pipeline.

## Entrées
- Chemin vers la base ChromaDB locale.

## Sorties
- Classe `VectorDBClient` capable d'effectuer des requêtes de similarité.

## Sous-tâches
1. Installer la bibliothèque `chromadb` si nécessaire.
2. Créer `services/vector_db_client.py` avec une classe initialisant la connexion.
3. Implémenter une méthode `search(query_embedding, top_k)` retournant les passages les plus proches.
4. Prévoir un système de pagination ou de limite des résultats.

## Conseils d'implémentation
- Rendre le chemin de la base configurable via les variables d'environnement.
- Ajouter un petit script de test pour vérifier la connexion.
