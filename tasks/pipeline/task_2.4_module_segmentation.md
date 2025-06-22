# Tâche 2.4 - Développement du Module de Segmentation

## Objectif
Segmenter les textes en morceaux cohérents pour la vectorisation.

## Entrées
- Texte extrait par les modules précédents.

## Sorties
- Liste de "chunks" de taille homogène (ex. 150 mots).

## Sous-tâches
1. Créer une fonction `chunk_text(text, size=150)` dans `segmenter.py`.
2. S'assurer que les coupures n'interrompent pas les phrases lorsque c'est possible.
3. Retourner la liste des segments pour la vectorisation ultérieure.
4. Conserver la trace de l'origine (nom du fichier, position du chunk) pour les métadonnées.

## Conseils d'implémentation
- Utiliser des expressions régulières ou `nltk` pour gérer la découpe sur les phrases.
- Prévoir des tests pour valider la taille des segments.
