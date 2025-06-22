# Tâche 4.2 - Tests d'Intégration du Backend

## Objectif
Vérifier que l'ensemble des endpoints fonctionne correctement avec les services associés.

## Entrées
- Backend assemblé via la tâche 4.1.
- Accès à une instance de base vectorielle et au LLM (ou mocks).

## Sorties
- Suite de tests automatisés et rapport de couverture.

## Sous-tâches
1. Utiliser `pytest` et `httpx` pour écrire des tests sur `/chat` et `/webhook`.
2. Simuler les réponses du LLM avec un client mock pour éviter les appels réels.
3. Vérifier que les appels au pipeline déclenchent bien le moteur proactif.
4. Inclure ces tests dans un workflow automatisé (GitHub Actions ou équivalent).

## Conseils d'implémentation
- Isoler l'environnement de test pour ne pas polluer la base de données réelle.
- Générer un rapport de couverture pour identifier les zones non testées.
