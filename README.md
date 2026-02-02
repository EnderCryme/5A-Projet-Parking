
# 🅿️ Système de Parking Modulable Intelligent (PSM)

![Status](https://img.shields.io/badge/Status-Prototype_Fonctionnel-success)
![Architecture](https://img.shields.io/badge/Architecture-Distributed_IoT-blueviolet)

**Plateformes :**
![BeagleY-AI](https://img.shields.io/badge/Brain-BeagleY--AI-blue)
![STM32](https://img.shields.io/badge/Edge-STM32F746-green)
![FPGA](https://img.shields.io/badge/Control-Nexys_A7--100T-orange)

**Stack Technique :**
![Languages](https://img.shields.io/badge/Code-C_%7C_Python_%7C_Verilog-lightgrey)
![OS](https://img.shields.io/badge/OS-Linux_%7C_Zephyr_RTOS-yellow)
![Protocol](https://img.shields.io/badge/Com-MQTT_%7C_Ethernet-red)

---

## 👥 Équipe Projet
* **FALDA Andy**
* **CAUQUIL Vincent**
* **ES-SRIEJ Youness**
* **CLERVILLE Annabelle**

---

## 📖 Description du Projet

Ce projet implémente un écosystème complet de gestion de parking. Il démontre une architecture distribuée où chaque module (Cerveau, Interface, Actionneur) communique sur un réseau local via le protocole **MQTT**.

Le système combine :
1.  **Intelligence Artificielle (OCR)** pour la lecture de plaques d'immatriculation ANPR.
2.  **Système Temps Réel (Zephyr)** pour l'interaction utilisateur et la gestion RFID.
3.  **Accélération Matérielle (FPGA/SoC RISC-V)** pour le pilotage précis des barrières motorisées.

---

## 🛠 Architecture & Réseau

Le système repose sur un réseau local Ethernet fermé. La **BeagleY-AI** agit comme le nœud central (Broker MQTT & Serveur Web).

### 🌐 Configuration IP (Statique)

| Module | Rôle | OS / Firmware | Adresse IP |
| :--- | :--- | :--- | :--- |
| **BeagleY-AI** | **Cerveau** : Broker MQTT, OCR, Dashboard Web | Linux (Debian) | `192.168.78.2` |
| **STM32 F7** | **Entrée** : RFID, Écran Tactile, Capteurs | Zephyr RTOS | `192.168.78.3` |
| **FPGA Nexys** | **Moteurs** : Driver Barrières, SoC Custom | Linux (Buildroot) | `192.168.78.10` |

### 📡 Synoptique des Flux MQTT

| Topic | Source | Destination | Description |
| :--- | :--- | :--- | :--- |
| `RFID/ID` | STM32 | BeagleY | Envoi de l'UID du badge scanné. |
| `RFID/CMD` | BeagleY | STM32 | Réponse d'accès (`UNLOCK` / `DENY`). |
| `parking/barrier`| BeagleY | FPGA | Ordre d'ouverture/fermeture physique. |
| `video/stream` | BeagleY | Dashboard | Flux vidéo temps réel de la caméra. |

---

## 📂 Structure du Dépôt

```text
├── gateware/                # 🧱 FPGA (Logique Programmable)
│   └── fpga/                # Sources SoC LiteX + VexRiscv
│
├── hardware/                # ⚙️ Conception Mécanique & PCB
│   ├── model3D/             # Fichiers CAO Onshape (Barrières, boîtiers)
│   └── pcb-designs/         # Schémas des cartes filles
│
├── software/                # 💻 Codes Sources
│   ├── sw-BBY-camera/       # [Python] Serveur, OpenCV, Tesseract
│   ├── sw-FPGA-barrieres/   # [C/Linux] Driver moteurs pour le SoC FPGA
│   ├── sw-STM32-ascenseur/  # [C/Zephyr] Gestion de l'ascenseur
│   └── sw-STM32-rfid/       # [C/Zephyr] Gestion principale Entrée (RFID/UI)
│
└── references/              # 📚 Documentation technique & PDF Projet
```

---

## 🧩 Détails des Modules

### 1. BeagleY-AI (Le Cerveau)
* **Traitement d'image :** Utilisation d'**OpenCV** (localisation, recadrage) et **Tesseract** (OCR) pour extraire les numéros de plaque.
* **Algorithme de Vote :** Validation de la plaque sur 3 images consécutives (par vote) pour fiabiliser la lecture.
* **Dashboard :** Interface Web HTML/CSS hébergée localement pour le monitoring vidéo et l'état du parking.

### 2. STM32F746 (L'Interface Physique)
* **Identification :** Lecteur RFID RC522 sur bus SPI.
* **Interaction :** IHM tactile développée avec **LVGL** (Feedback utilisateur, codes erreur).
* **Éco-gestion :** Gestion de la luminosité (Photo-résistance) et extinction automatique de l'écran si aucune présence véhicule n'est détectée.
* **Sécurité :** Badge "Maître" codé en dur pour forcer l'ouverture ou accéder au menu maintenance.

### 3. FPGA Nexys A7 (La Puissance)
* **SoC Custom :** Implémentation d'un processeur **RISC-V 32-bits** sur le FPGA via LiteX.
* **Linux Embarqué :** Le FPGA fait tourner un noyau Linux minimal capable de mapper les périphériques moteurs via `mmap`.
* **Motorisation :** Contrôle de puissance des barrières via drivers externes pilotés par le SoC.

---

## 🚀 Installation & Démarrage

### Pré-requis
* **Réseau :** Routeur ou Switch configuré pour le sous-réseau `192.168.78.x`.
* **Outils :**
    * [STM32] **West** (Zephyr Toolchain)
    * [FPGA] **Vivado** (Xilinx Lab Tools)
    * [Beagle] **Python 3**

### Procédure Rapide

1.  **BeagleY-AI (Lancement Serveur) :**
    ```bash
    cd software/sw-BBY-camera
    python3 main.py
    ```

2.  **STM32 (Build & Flash) :**
    ```bash
    # Depuis la racine du projet
    west build -b stm32f746g_disco software/sw-STM32-rfid
    west flash
    ```

3.  **FPGA (Bitstream & Boot) :**
    *   Ouvrir Vivado Hardware Manager.
    *   Charger le bitstream situé dans `gateware/fpga/v3-test-autorun`.
    *   *Résultat :* Le SoC démarre, charge le Linux depuis la carte SD et rejoint le réseau automatiquement.

---

## 📚 Références
* [Documentation Complète (PDF)](references/Projet_CAUQUIL_FALDA_CLERVILLE_ES-SRIEJ.pdf)
* [LiteX - Linux on RISC-V](https://github.com/litex-hub/linux-on-litex-vexriscv)
