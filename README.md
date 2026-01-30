# 🅿️ Projet Parking Système Modulable (PSM)

Ce projet implémente un système de gestion de parking intelligent, modulaire et connecté. Il repose sur une architecture distribuée combinant intelligence artificielle, systèmes temps réel et logique câblée/programmable.

## 👥 Équipe Projet
* **FALDA Andy**
* **CAUQUIL Vincent**
* **ES-SRIEJ Youness**
* **CLERVILLE Annabelle**

---

## 🏗️ Architecture Globale

Le système fonctionne sur un réseau local dédié où les différents modules communiquent via le protocole **MQTT**.

* **Cerveau (BeagleY-AI)** : Serveur central, traitement d'image (OCR), Dashboard Web.
* **Point d'entrée (STM32)** : Gestion des accès RFID, IHM tactile, capteurs environnementaux.
* **Actionneurs (FPGA)** : Contrôle matériel bas niveau (Barrières, Moteurs) via un SoC RISC-V sous Linux.

### 🌐 Configuration Réseau (Adressage Statique)

Tous les périphériques sont connectés sur le même sous-réseau. Le serveur MQTT est hébergé sur la BeagleY-AI.

| Module | Rôle | Adresse IP |
| :--- | :--- | :--- |
| **BeagleY-AI** | Serveur / Broker MQTT / Web | `192.168.78.2` |
| **STM32 (RFID)** | Contrôle d'accès & UI | `192.168.78.3` |
| **FPGA (Nexys A7)** | Pilotage Barrières (SoC Linux) | `192.168.78.10` |

---

## 📂 Structure du Dépôt

```text
├── gateware/                # Code et configuration FPGA
│   └── fpga/                # Sources Verilog/LiteX pour le SoC RISC-V
├── hardware/                # Conception Mécanique et Électronique
│   ├── model3D/             # Fichiers CAO (Onshape) : Barrières, supports
│   └── pcb-designs/         # Schémas électroniques
├── software/                # Code source des différents modules
│   ├── sw-BBY-camera/       # Python : OpenCV/Tesseract + Serveur Web
│   ├── sw-FPGA-barrieres/   # C/Linux : Driver moteurs barrières
│   ├── sw-STM32-ascenseur/  # C/Zephyr : Gestion de l'ascenseur
│   └── sw-STM32-rfid/       # C/Zephyr : Gestion RFID RC522 + Écran tactile
└── references/              # Documentation et datasheets
```

---

## 🔧 Détails des Modules

### 1. BeagleY-AI (Le Cerveau)
* **OS** : Linux
* **Langages** : Python
* **Fonctionnalités** :
    * **Reconnaissance de plaques (LAPI)** : Utilisation d'OpenCV pour le traitement d'image et Tesseract (OCR) pour la lecture.
    * **Serveur Web** : Interface de supervision (Dashboard) en HTML/CSS pour visualiser le flux vidéo et l'état du parking.
    * **Logique de contrôle** : Validation des plaques via un système de vote (3 images consécutives).

### 2. STM32F746 Discovery (L'Entrée Physique)
* **OS** : Zephyr RTOS
* **Langage** : C
* **Fonctionnalités** :
    * **RFID (SPI)** : Lecture des badges via module RC522. Envoi des UID via MQTT (`RFID/ID`).
    * **Interface Homme-Machine** : Écran tactile pour feedback utilisateur (UNLOCK/DENY).
    * **Gestion Éclairage** : Capteur de luminosité (photo-résistance) et pilotage relais 12V.
    * **Modes Spéciaux** : Badge "Maître" pour accès maintenance et forçage mode éco.

### 3. FPGA Nexys A7-100T (Le Contrôle Moteur)
* **Architecture** : SoC Custom (LiteX + VexRiscv)
* **OS Embarqué** : Linux (Buildroot)
* **Fonctionnalités** :
    * **Gestion Barrières** : Pilotage de drivers moteurs pas-à-pas.
    * **Connectivité** : Liaison Ethernet hardware mappée via AXI.
    * **Commande** : Réception des ordres `open/close` via MQTT et traduction en signaux moteurs.

---

## 🚀 Installation et Démarrage

### Pré-requis
* **STM32** : Environnement Zephyr RTOS installé (`west`).
* **BeagleY-AI** : Python 3, `paho-mqtt`, `opencv-python`, `pytesseract`.
* **FPGA** : Vivado et Toolchain LiteX/RISC-V.

### Instructions Rapides
1. **Réseau** : Configurer le routeur ou le switch pour le sous-réseau `192.168.78.x`.
2. **BeagleY-AI** : Lancer le script principal dans `software/sw-BBY-camera`.
3. **STM32** : Compiler et flasher le firmware :
   ```bash
   west build -b stm32f746g_disco software/sw-STM32-rfid
   west flash
   ```
4. **FPGA** : Charger le bitstream situé dans `gateware/fpga/v3-test-autorun` et démarrer le noyau Linux via TFTP ou SD.

---

## 📚 Références
Pour plus de détails techniques, consulter le document : `references/Projet_CAUQUIL_FALDA_CLERVILLE_ES-SRIEJ.pdf`
