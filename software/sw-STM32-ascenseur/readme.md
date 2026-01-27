# Système de Contrôle d'Ascenseur Intelligent (STM32 Node)

![Status](https://img.shields.io/badge/Status-Prototype-yellow)
![Platform](https://img.shields.io/badge/Platform-STM32F746G--DISCO-blue)
![OS](https://img.shields.io/badge/OS-Zephyr%20RTOS-green)
![Motor](https://img.shields.io/badge/Driver-TMC5160-red)

## 📖 Description du Projet

Ce dépôt contient le firmware d'un système de contrôle d'ascenseur de précision. [cite_start]Le projet implémente un pilotage avancé de moteur pas-à-pas associé à un asservissement par capteur de distance laser pour garantir un positionnement exact aux différents étages.

[cite_start]Le système intègre une gestion complète de la sécurité (fin de course, arrêts d'urgence) et une rampe d'accélération logicielle pour assurer des mouvements fluides et sécurisés.

### 🚀 Fonctionnalités Clés

* [cite_start]**Pilotage TMC5160 (SPI) :** Gestion avancée du driver moteur avec surveillance de l'état du pont en H et résilience automatique[cite: 1, 12, 16].
* [cite_start]**Recalibrage Automatique :** Séquence d'initialisation au démarrage pour définir le point zéro via le capteur de fin de course[cite: 1, 7, 8].
* [cite_start]**Positionnement Laser :** Utilisation du capteur VL53L0X (I2C) pour le recalage en temps réel et la correction de dérive[cite: 1, 15].
* [cite_start]**Rampe d'Accélération :** Algorithme de vitesse dynamique (trapézoïdale) pour limiter les secousses mécaniques.
* [cite_start]**Gestion Multi-étages :** Support natif de 3 niveaux configurables avec mémorisation des appels[cite: 1, 9, 10, 11].
* [cite_start]**Sécurité Active :** Surveillance continue du bouton d'arrêt d'urgence et détection de collision lors de la descente[cite: 1, 7].

## 🛠 Architecture Matérielle

* [cite_start]**MCU :** STM32F746NG (Arm Cortex-M7) 
* [cite_start]**Board :** STM32F746G-DISCO 
* [cite_start]**Driver Moteur :** TMC5160 SilentStepStick (SPI) [cite: 1, 12, 13]
* [cite_start]**Capteur de distance :** VL53L0X (Laser Time-of-Flight) [cite: 1, 15]

### Pinout & Connexions (Overlay)

| Périphérique | Pin STM32 | Type | Description |
| :--- | :--- | :--- | :--- |
| **Moteur STEP** | `PA15` | GPIO Out | [cite_start]Signal de pas (Step) [cite: 5] |
| **Moteur DIR** | `PI2` | GPIO Out | [cite_start]Direction du mouvement [cite: 6] |
| **Moteur ENABLE**| `PI3` | GPIO Out | [cite_start]Activation du driver (Actif Low) [cite: 4] |
| **SPI2 (TMC)** | `PB14/PB15/PI1`| SPI | [cite_start]Bus de configuration du driver [cite: 12] |
| **TMC CS** | `PA8` | GPIO Out | [cite_start]Chip Select SPI du TMC5160 [cite: 12] |
| **VL53L0X** | `I2C1` | I2C | [cite_start]Capteur de distance laser [cite: 15] |
| **Fin de Course** | `PH6` | GPIO In | [cite_start]Capteur de contact (Point Zéro) [cite: 7, 8] |
| **Bouton Étage 0**| `PG6` | GPIO In | [cite_start]Appel Rez-de-chaussée (Actif Low) [cite: 8, 9] |
| **Bouton Étage 1**| `PG7` | GPIO In | [cite_start]Appel Niveau 1 (Actif Low) [cite: 9, 10] |
| **Bouton Étage 2**| `PI0` | GPIO In | [cite_start]Appel Niveau 2 (Actif Low) [cite: 10, 11] |

## ⚙️ Configuration Logicielle (Calibration)

Le firmware utilise les paramètres de calibration suivants définis dans `main.c` :

* [cite_start]**Étage 0 :** 0 mm 
* [cite_start]**Étage 1 :** 170 mm 
* [cite_start]**Étage 2 :** 336 mm 
* [cite_start]**Résolution :** 350 pas / mm 
* [cite_start]**Vitesse :** Rampe entre 1200µs (min) et 200µs (max) par pas 

## 📡 Compilation & Build

Le projet repose sur **Zephyr RTOS**.

### Pré-requis
* [cite_start]Zephyr SDK installé[cite: 16].
* [cite_start]Outil West configuré.

### Commandes

```bash
# Compiler le projet pour la STM32F746G-DISCO
west build -p -b stm32f746g_disco

# Flasher la carte
west flashn --runner openocd

