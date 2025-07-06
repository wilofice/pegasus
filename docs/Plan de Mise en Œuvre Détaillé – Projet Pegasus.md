### **Plan de Mise en Œuvre Détaillé – Projet Pegasus**

Ce document présente le plan de développement du projet Pegasus, décomposé en tâches spécifiques pour chaque composant majeur de l'architecture.

---

### **Partie 1 : Data Pipeline**

**Objectif :** Créer un système autonome et robuste qui transforme les données brutes (audio, textes, emails) en une mémoire vectorielle interrogeable.

**Fichiers de Test Proposés :**
1.  **Fichier Audio :** `journal_intime_22-06-2025.mp3` (Un enregistrement audio de vos pensées).
2.  **Fichier Texte :** `export_whatsapp_famille.txt` (Un export d'une conversation WhatsApp).
3.  **Fichier Email :** `email_confirmation_vol_italie.eml` (Un email de confirmation de réservation).

**Plan de Tâches :**

| # | Tâche | Description Détaillée | Dépendances |
| :-- | :--- | :--- | :--- |
| **1.0** | **Phase 1 : Configuration de l'Environnement** | | |
| 1.1 | Installation des Prérequis | Installer Python 3.9+, pip, et l'outil de traitement audio `ffmpeg` sur le serveur personnel. | - |
| 1.2 | Création de la Structure de Dossiers | Mettre en place l'arborescence définie dans le plan d'organisation : `data_pipeline/`, `source_data/`, `database/`, `logs/`. | - |
| 1.3 | Mise en Place de l'Environnement Virtuel | Créer un environnement virtuel Python (`python -m venv venv`) et installer les dépendances (`pip install -r requirements.txt`). | Tâche 1.1 |
| **2.0** | **Phase 2 : Développement du Cœur de Traitement** | | |
| 2.1 | Développement du Module de Surveillance | Implémenter la surveillance du dossier `source_data/` avec la bibliothèque `watchdog` pour détecter la création de nouveaux fichiers. | Tâche 1.3 |
| 2.2 | Développement du Module de Transcription Audio | Intégrer `openai-whisper` pour transcrire les fichiers audio détectés (.mp3, .m4a, etc.) en texte brut. | Tâche 2.1 |
| 2.3 | **Développement du Module d'Extraction de Texte** | **Point clé :** Gérer les différents types de fichiers texte :<br> - **Fichiers .txt/.md :** Lecture simple.<br> - **Exports WhatsApp :** Créer une fonction pour nettoyer le format `[JJ/MM/AA HH:MM] Nom: Message` afin de ne garder que le contenu textuel pertinent.<br> - **Fichiers .eml (Emails) :** Utiliser une bibliothèque Python comme `eml_parser` pour extraire de manière fiable le corps du texte de l'email, en ignorant les en-têtes et signatures non pertinents. | Tâche 2.1 |
| 2.4 | Développement du Module de Segmentation | Créer une fonction de "chunking" qui segmente les textes extraits (qu'ils viennent d'un audio, d'un .txt ou d'un email) en morceaux de taille cohérente (ex: 150 mots). | Tâche 2.2, 2.3 |
| 2.5 | Développement du Module de Vectorisation | Utiliser `sentence-transformers` pour convertir chaque morceau de texte en un vecteur numérique (embedding). | Tâche 2.4 |
| 2.6 | Développement du Module de Stockage | Intégrer `chromadb` pour stocker les vecteurs, les textes originaux des chunks, et les métadonnées (nom du fichier source, date) dans la base de données locale. | Tâche 2.5 |
| 2.7 | Développement du Module de Notification | Implémenter l'envoi d'un webhook (via `requests`) à l'URL du backend après chaque traitement de fichier réussi. | Tâche 2.6 |
| **3.0** | **Phase 3 : Finalisation et Test** | | |
| 3.1 | Intégration et Orchestration | Assembler tous les modules dans le script final `pipeline.py`. Ajouter une gestion robuste des erreurs et des logs détaillés. | Tâches 2.x |
| 3.2 | Tests Unitaires | Tester le pipeline avec les 3 fichiers de test proposés pour s'assurer que chaque type de source est correctement traité et stocké. | Tâche 3.1 |

---

### **Partie 2 : Backend**

**Objectif :** Créer une API sécurisée qui sert d'intermédiaire entre le frontend et la mémoire de Pegasus, et qui héberge le moteur d'analyse proactive.

**Plan de Tâches :**

| # | Tâche | Description Détaillée | Dépendances |
| :-- | :--- | :--- | :--- |
| **1.0** | **Phase 1 : Configuration de l'Environnement** | | |
| 1.1 | Installation et Configuration de FastAPI | Mettre en place un projet FastAPI de base. Configurer la structure de dossiers (`api/`, `core/`, `services/`). | - |
| 1.2 | Dockerisation du Backend | Créer le `Dockerfile` pour permettre au backend de tourner dans un conteneur isolé, facilitant le déploiement. | Tâche 1.1 |
| **2.0** | **Phase 2 : Développement des Endpoints API** | | |
| 2.1 | Développement du Routeur de Chat (`/chat`) | Créer le endpoint qui reçoit les messages de l'utilisateur depuis le frontend. Mettre en place la sécurité (ex: token d'authentification). | Tâche 1.1 |
| 2.2 | Développement du Routeur de Webhook (`/webhook`) | Créer le endpoint qui reçoit la notification du Data Pipeline et qui déclenchera l'analyse proactive. | Tâche 1.1 |
| **3.0** | **Phase 3 : Développement de la Logique Métier** | | |
| 3.1 | Création du Client pour la Base Vectorielle | Développer une classe dans `services/vector_db_client.py` pour se connecter et interroger la base ChromaDB créée par le pipeline. | - |
| 3.2 | Création du Client pour le LLM | Développer une classe dans `services/llm_client.py` pour envoyer des prompts à l'API du LLM externe (OpenAI ou Anthropic). | - |
| 3.3 | Implémentation de l'Orchestrateur (Mode Réactif) | Coder la logique dans `core/orchestrator.py` qui, pour une requête utilisateur : 1. Interroge la base vectorielle (via Tâche 3.1). 2. Construit le prompt avec le contexte. 3. Appelle le LLM (via Tâche 3.2). 4. Renvoie la réponse. | Tâche 3.1, 3.2 |
| 3.4 | Implémentation du Moteur Proactif | Coder la logique dans `core/proactive_engine.py` qui, sur réception d'un webhook, analyse les nouvelles données et décide s'il faut initier une conversation. | Tâche 3.1, 3.2 |
| **4.0** | **Phase 4 : Intégration et Test** | | |
| 4.1 | Assemblage des Composants | Connecter les routeurs API à la logique métier. Gérer la configuration (clés d'API) de manière sécurisée. | Tâches 2.x, 3.x |
| 4.2 | Tests d'Intégration | Simuler des appels aux endpoints pour vérifier que toute la chaîne fonctionne comme prévu. | Tâche 4.1 |

---

### **Partie 3 : Frontend (Flutter)**

**Objectif :** Développer une interface de chat mobile, fluide et intuitive, capable d'interagir avec le backend en temps réel et de recevoir des notifications.

**Plan de Tâches :**

| # | Tâche | Description Détaillée | Dépendances |
| :-- | :--- | :--- | :--- |
| **1.0** | **Phase 1 : Configuration du Projet Flutter** | | |
| 1.1 | Initialisation du Projet | Créer un nouveau projet Flutter. Mettre en place la structure de dossiers (`lib/`, `screens/`, `widgets/`, etc.). | - |
| 1.2 | Ajout des Dépendances Clés | Ajouter les packages nécessaires dans `pubspec.yaml` (ex: `http` pour les appels API, `flutter_riverpod` pour la gestion d'état, `firebase_messaging` pour les notifications). | Tâche 1.1 |
| **2.0** | **Phase 2 : Développement de l'Interface Utilisateur (UI)** | | |
| 2.1 | Conception de l'Écran de Chat | Créer `chat_screen.dart`. Développer les widgets `MessageBubble` (pour les messages de l'utilisateur et de Pegasus) et `MessageComposer` (champ de saisie et bouton micro). | Tâche 1.2 |
| 2.2 | Intégration du Thème Visuel | Définir les couleurs, polices et le style général de l'application pour une expérience apaisante. | Tâche 2.1 |
| **3.0** | **Phase 3 : Intégration des Services** | | |
| 3.1 | Développement du Client API | Dans `pegasus_api_client.dart`, écrire les fonctions pour communiquer avec le backend (envoyer un message au `/chat`). | Backend prêt |
| 3.2 | Implémentation du Service Vocal | Utiliser les packages Flutter pertinents pour intégrer le Speech-to-Text (pour parler à Pegasus) et le Text-to-Speech (pour que Pegasus réponde à voix haute). | - |
| 3.3 | Configuration des Notifications Push | Intégrer Firebase à l'application Flutter et configurer le `notification_service.dart` pour recevoir les notifications envoyées par le backend lorsque le mode proactif se déclenche. | Backend prêt |
| **4.0** | **Phase 4 : Gestion de l'État et Finalisation** | | |
| 4.1 | Mise en Place de la Gestion d'État | Utiliser `Riverpod` (ou `Provider`) pour gérer l'état de la conversation (la liste des messages qui s'affiche à l'écran) de manière efficace. | Tâche 2.1 |
| 4.2 | Connexion UI <> Logique | Lier l'interface utilisateur aux services : l'envoi d'un message dans l'UI appelle le client API, qui met à jour l'état de la conversation avec la réponse. | Tâches 3.x, 4.1 |
| 4.3 | Tests sur Appareil Réel | Compiler et tester l'application sur un véritable appareil iOS et Android pour s'assurer que tout fonctionne comme prévu. | Tâche 4.2 |