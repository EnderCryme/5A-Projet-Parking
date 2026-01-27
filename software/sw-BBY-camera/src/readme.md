#  Modules Sources (Core Logic)

![Type](https://img.shields.io/badge/Type-Backend%20Logic-blue)
![Language](https://img.shields.io/badge/Python-3.9-yellow)
![Dependencies](https://img.shields.io/badge/Libs-OpenCV%20|%20Flask%20|%20PahoMQTT-orange)

## 📖 Vue d'ensemble

Ce dossier contient l'ensemble des modules backend (Managers) qui constituent l'intelligence du système.
L'architecture est **modulaire** : chaque fichier gère un aspect spécifique du matériel ou de la logique métier, orchestré par le `main.py` situé à la racine.

## 🛠 Liste des Modules

| Fichier | Classe Principale | Rôle Technique |
| :--- | :--- | :--- |
| **`camera_manager.py`** | `CameraManager` | Pipeline de vision : Acquisition, Détection (Haar) et OCR (Tesseract). |
| **`db_manager.py`** | `DbManager` | Interface CRUD pour la base de données SQLite (Users, Historique). |
| **`mqtt_manager.py`** | `MqttManager` | Client asynchrone pour la communication IoT (RFID, Barrières). |
| **`lcd_manager.py`** | `LcdManager` | Driver SPI pour l'affichage matriciel (MAX7219) avec gestion du scroll. |
| **`sensor_manager.py`** | `SensorManager` | Driver SPI pour le capteur environnemental BME680 (Temp/Hum). |
| **`local_bridge.py`** | *Script* | Version allégée pour déploiement "Edge" (voir section dédiée). |

---

## 👁️ Gestion Vision (`camera_manager.py`)

Ce module gère un thread dédié à la capture vidéo et au traitement d'image pour ne pas bloquer le serveur Web.

* **Algorithme :** Utilise `Haar Cascade` (XML) pour localiser la plaque, puis `Pytesseract` pour lire le texte.
* **Système de Vote :** Pour éviter les erreurs de lecture, le module stocke les résultats dans un `vote_buffer`. Une plaque n'est validée que si elle apparaît **3 fois** consécutivement (configurable via `SAMPLES_TO_TAKE`).
* **Optimisation :** Redimensionne l'image par 0.5x avant la détection pour économiser du CPU.

## 💾 Base de Données (`db_manager.py`)

Wrapper autour de **SQLite**. Il gère la persistance des données et la logique métier du parking.

* **Tables Gérées :**
  * `users` : Comptes conducteurs et administrateurs.
  * `plaques` : Plaques d'immatriculation (Liaison 1-N).
  * `badges` : UIDs des cartes RFID (Liaison 1-N).
  * `historique` : Journal des entrées/sorties avec calcul automatique de l'état `GARÉ` / `PARTI`.
* **Sécurité :** Les mots de passe sont hashés en **SHA-256** avant stockage.

## 📟 Drivers Matériels (`lcd_manager.py` & `sensor_manager.py`)

Ces modules pilotent le matériel via le bus **SPI**.

* **Mode Simulation :** Ces deux drivers intègrent une détection automatique de l'environnement (`IS_REAL_HARDWARE`). Si le script tourne sur un PC Windows (sans SPI), ils basculent en mode "Mock" (simulation) pour permettre le développement sans la BeagleBoard.
* **LcdManager :** Gère une police de caractères personnalisée (5x7) et le défilement fluide du texte.
* **SensorManager :** Lit la température et l'humidité, avec gestion des erreurs de lecture (valeurs aberrantes > 100°C ignorées).

## ☁️ Edge Computing (`local_bridge.py`)

Ce script est une alternative au `main.py` destinée aux architectures distribuées.
Il permet de déporter l'intelligence dans le Cloud tout en gardant une exécution locale rapide pour :
1. Lire la plaque (IA locale).
2. Envoyer le résultat en MQTT.
3. Attendre l'ordre d'ouverture venant du serveur distant.

