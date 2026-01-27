# Système de Gestion Centralisé (BeagleBone Node)

![Status](https://img.shields.io/badge/Status-Prototype-yellow)
![Platform](https://img.shields.io/badge/Hardware-BeagleY%20AI-green)
![Language](https://img.shields.io/badge/Language-Python%203.12-3776AB?logo=python&logoColor=white)
![Framework](https://img.shields.io/badge/Backend-Flask-000000?logo=flask&logoColor=white)
![Vision](https://img.shields.io/badge/Vision-OpenCV-5C3EE8?logo=opencv&logoColor=white)

## 📖 Description du Projet

Ce dépôt contient le "cerveau" du système de parking intelligent. Exécuté sur une **BeagleBone Black / BeagleY-AI**, ce nœud centralise la logique métier, la gestion de la base de données et le traitement d'images.

Il agit comme une passerelle (Gateway) qui coordonne les périphériques via MQTT (comme le nœud STM32), offre une interface Web d'administration et effectue la reconnaissance optique de caractères (ALPR) en temps réel.

### Fonctionnalités Clés

* **Reconnaissance LAPI (ALPR) :** Détection et lecture automatique des plaques d'immatriculation via **OpenCV** (Haar Cascades) et **Tesseract OCR**.
* **Serveur Web (Flask) :** Dashboard complet pour l'administration (IT) et les clients (User) avec streaming vidéo MJPEG.
* **Base de Données (SQLite) :** Gestion persistance des utilisateurs, historique des entrées/sorties et droits d'accès.
* **Logique de Contrôle :** Moteur de décision fusionnant les données RFID (MQTT) et Vidéo pour piloter les barrières.
* **Affichage Local (SPI) :** Pilotage d'une matrice LED/LCD pour les messages d'accueil et la météo locale.
* **Mode Hybride :** Capacité de fonctionner en mode "Simulation" sur PC (Windows) ou en mode "Matériel Réel" sur Linux (détection automatique).

## 🛠 Architecture Matérielle

* **SBC :** BeagleBone Black Wireless / BeagleY-AI (Debian Linux)
* **Vision :** Webcams USB (Entrée/Sortie)
* **Affichage :** Matrice LED (MAX7219) via SPI
* **Capteurs :** BME680 (Température/Pression/Humidité)

### Pinout & Connexions

| Périphérique | Pin BeagleBone | Bus | Description |
| :--- | :--- | :--- | :--- |
| **LCD / Matrice** | `P9_17` (CS0) | SPI0 | Affichage messages défilants |
| **Capteur BME680** | `P9_28` (CS1) | SPI0 | Télémétrie environnementale |
| **Caméra Entrée** | USB Host | USB | Flux Vidéo 1 (`/vid_in`) |
| **Caméra Sortie** | USB Host | USB | Flux Vidéo 2 (`/vid_out`) |

## 📡 API MQTT

Le serveur agit comme le maître logique sur le réseau local.

| Topic | Direction | Payload | Description |
| :--- | :--- | :--- | :--- |
| `RFID/ID` | Sub (In) | `[UID]` | Réception d'un badge scanné par le STM32. |
| `RFID/CMD` | Pub (Out) | `UNLOCK_READY` | Indique au STM32 que le badge est valide. |
| `RFID/CMD` | Pub (Out) | `DENY` | Indique au STM32 que l'accès est refusé. |
| `parking/barrier_x/state` | Pub (Out) | `OPEN` / `CLOSE` | Ordre d'ouverture des barrières physiques. |
| `RFID/ADD` | Sub (In) | `[UID]` | Demande d'ajout rapide d'un badge (Admin). |

## ☁️ Ouverture : Architecture Cloud & Edge Computing

Actuellement, le projet fonctionne en mode "autonome" (le serveur Web et l'IA tournent sur la même machine). Pour un déploiement réel à grande échelle (ex: via Render ou AWS), l'architecture évoluerait vers un modèle **IoT Edge** :

1. **Sur site (Edge Node)** : Un script python léger (`local_bridge.py`) tourne sur la BeagleBone. Il gère :
    * L'acquisition vidéo et l'OCR (Traitement local pour rapidité).
    * Le pilotage physique (GPIO) des barrières et écrans LCD.
    * La communication sécurisée via **MQTT (TLS)** vers le Cloud.

2. **Sur le Cloud (Server Node)** : L'application Flask (`main_v08d.py`) est hébergée sur un serveur distant. Elle gère :
    * La base de données centralisée.
    * L'interface administrateur accessible de partout.
    * La validation des entrées : elle reçoit la plaque via MQTT, vérifie les droits, et renvoie l'ordre d'ouverture à la BeagleBone.

3. **Flux Vidéo** : Plutôt que de streamer de la vidéo lourde, le nœud local envoie des **Snapshots (images instantanées)** en base64 via MQTT ou via un tunnel WebRTC lors des événements importants (détection, effraction), optimisant ainsi la bande passante 4G/5G des parkings isolés.

## ⚙️ Installation & Démarrage

Le projet nécessite Python 3.9+ et les drivers système.

### Pré-requis

```bash
# Installation des dépendances système (Debian/Ubuntu)
sudo apt update
sudo apt install python3-opencv tesseract-ocr libopenjp2-7

# Installation des bibliothèques Python
pip install -r requirements.txt

```

### Lancement

Le système détecte automatiquement s'il tourne sur un PC (Simulation) ou sur la BeagleBone (SPI activé).

```bash
# Lancement du serveur principal
python3 main_v08d.py

```

*L'interface web est accessible sur `http://<IP_BEAGLEBONE>:5000*`
