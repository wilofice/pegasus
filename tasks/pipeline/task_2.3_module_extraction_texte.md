# Tâche 2.3 - Développement du Module d'Extraction de Texte

## Objectif
Extraire le contenu textuel pertinent des différents formats de fichiers (texte simple, export WhatsApp, email).

## Entrées
- Fichier .txt/.md, export WhatsApp ou .eml présent dans `source_data/`.

## Sorties
- Texte nettoyé prêt pour la segmentation.

## Sous-tâches
1. Pour les fichiers `.txt` ou `.md`, lire simplement le contenu.
2. Pour les exports WhatsApp, supprimer la partie `[JJ/MM/AA HH:MM] Nom:` afin de ne garder que le message.
3. Pour les emails `.eml`, utiliser `eml_parser` pour extraire le corps de texte en ignorant entêtes et signatures.
4. Retourner le texte pur au module de segmentation.

## Conseils d'implémentation
- Factoriser le code dans un module `text_extractor.py`.
- Prévoir des tests unitaires sur des échantillons de fichiers.
