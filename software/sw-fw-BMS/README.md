# 🔋 Firmware/Software BMS Intelligent 

## 📖 Présentation Logicielle

Ce dépôt contient le firmware de contrôle pour le sous-ensemble BMS. Développé en **MicroPython**, ce logiciel transforme le RP2350 en une unité de gestion intelligente capable de dialoguer avec le contrôleur **BQ40Z50** via le protocole **SMBus**.

Le code assure la lecture des paramètres critiques de la batterie, la gestion de l'affichage local et le pilotage des sécurités de l'étage de puissance.

## 🛠️ Architecture du Firmware/Software

### 1. Communication SMBus / I2C

Le firmware exploite le bus I2C (GPIO 8 & 9) à une fréquence de 400kHz pour interroger les registres standards du BQ40Z50:

* 
**V Tension (`0x09`)** : Acquisition en millivolts.


* 
**A Courant (`0x0A`)** : Lecture signée gérant la charge (+) et la décharge (-).


* 
**% État de Charge (`0x0D`)** : Récupération directe du SoC (State of Charge).


* 
**T Température (`0x08`)** : Conversion de Kelvin (0.1°K) vers Celsius.



### 2. Logique de Contrôle & Sécurité

Le firmware agit comme le superviseur du système via des signaux de contrôle dédiés :

* 
**Signal CTRL (`GPIO 44`)** : Pilotage de la grille du MOSFET DMP3035 pour l'activation des sorties USB-C 5V@3A.


* 
**Monitoring ADC (`GPIO 43`)** : Surveillance de la tension VBUS via un pont diviseur de tension (47k/33k) pour valider la régulation.



## 🚀 Installation & Autorun

### 1. Préparation du RP2350

* Téléchargez le firmware MicroPython `.uf2` pour **Pico 2** sur [micropython.org](https://micropython.org/download/RPI_PICO2/).
* Maintenez le bouton **SW2** (USB_BOOT) enfoncé et branchez le module en USB.


* Copiez le fichier `.uf2` dans le lecteur `RPI-RP3`.

### 2. Déploiement du Code

Utilisez **Thonny IDE** pour téléverser les fichiers à la racine du microcontrôleur :

* 
`ssd1306.py` : Pilote basse couche pour l'écran OLED.


* **`main.py`** : Script principal contenant la boucle de monitoring (se lance automatiquement à l'allumage).

## 📡 Interface Utilisateur (OLED)

L'affichage est rafraîchi toutes les secondes et présente un dashboard complet:

* **Ligne 1** : Tension (V) et Température (°C).
* **Ligne 2** : Courant de charge/décharge (A).
* **Ligne 3** : Barre de progression graphique du niveau de batterie.

## 📂 Structure des fichiers Software

* `/firmware/main.py` : Logique métier et boucle principale.
* `/firmware/ssd1306.py` : Bibliothèque d'affichage I2C.
* `/docs/registers.md` : Liste des commandes SMBus utilisées.

---

> [!TIP]
> **Le savais-tu ?** En nommant ton fichier `main.py`, le RP2350 l'exécute dès qu'il reçoit du courant, même sans être branché à un ordinateur. C'est ce qu'on appelle l'**autorun**.

### 📑 Table des Commandes I2C (SMBus/Relier aux registres visibles sur le BQstudio)

| Commande | Registre (Hex) | Unité | Description |
| --- | --- | --- | --- |
| **Temperature** | `0x08` | 0.1°K | Température interne du pack (convertie en °C dans le code).

 |
| **Voltage** | `0x09` | mV | Tension totale aux bornes du pack batterie.

 |
| **Current** | `0x0A` | mA | Courant instantané (positif = charge, négatif = décharge).

 |
| **RelativeSoC** | `0x0D` | % | État de charge restant par rapport à la capacité actuelle.

 |

---



