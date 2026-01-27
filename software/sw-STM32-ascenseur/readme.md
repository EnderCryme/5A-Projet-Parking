# Système de Contrôle d'Ascenseur Intelligent (STM32 Node)

![Status](https://img.shields.io/badge/Status-Prototype-yellow)
![Platform](https://img.shields.io/badge/Platform-STM32F746G--DISCO-blue)
![OS](https://img.shields.io/badge/OS-Zephyr%20RTOS-green)
![Motor](https://img.shields.io/badge/Driver-TMC5160-red)

## 📖 Description du Projet

Ce dépôt contient le firmware d'un système de contrôle d'ascenseur de précision. Le projet implémente un pilotage avancé de moteur pas-à-pas associé à un asservissement par capteur de distance laser pour garantir un positionnement exact aux différents niveaux.

Le système intègre une gestion complète de la sécurité (fin de course, arrêts d'urgence) et une rampe d'accélération logicielle pour assurer des mouvements fluides et prévenir l'usure mécanique.

### 🚀 Fonctionnalités Clés

* **Pilotage TMC5160 (SPI) :** Gestion avancée du driver moteur avec surveillance d'état et résilience automatique en cas de défaut.
* **Recalibrage Automatique :** Séquence d'initialisation au démarrage pour définir le point zéro via capteur de fin de course.
* **Positionnement Laser (ToF) :** Utilisation du capteur VL53L0X pour le recalage en temps réel et la correction de dérive.
* **Rampe d'Accélération :** Algorithme de vitesse dynamique pour limiter les secousses lors des phases de départ et d'arrêt.
* **Gestion Multi-étages :** Support natif de 3 niveaux configurables avec système de mémorisation des appels en attente.
* **Sécurité Active :** Surveillance du bouton d'arrêt d'urgence et détection de collision/sol lors de la descente.

## 🛠 Architecture Matérielle

* **MCU :** STM32F746NG (Arm Cortex-M7)
* **Board :** STM32F746G-DISCO
* **Driver Moteur :** TMC5160 SilentStepStick
* **Capteur :** VL53L0X (Laser Distance)

### Pinout & Connexions (Overlay)

| Périphérique | Pin STM32 | Type | Description |
| :--- | :--- | :--- | :--- |
| **Moteur STEP** | `PA15` | GPIO Out | Signal de pas |
| **Moteur DIR** | `PI2` | GPIO Out | Direction du mouvement |
| **Moteur ENABLE**| `PI3` | GPIO Out | Activation driver (Actif Low) |
| **TMC CS** | `PA8` | GPIO Out | Chip Select SPI |
| **Fin de Course** | `PH6` | GPIO In | Capteur Point Zéro (D6) |
| **Appel Étage 0**| `PG6` | GPIO In | Bouton Rez-de-chaussée (D2) |
| **Appel Étage 1**| `PG7` | GPIO In | Bouton Niveau 1 (D4) |
| **Appel Étage 2**| `PI0` | GPIO In | Bouton Niveau 2 (D5) |

## ⚙️ Paramètres de Calibration (main.c)

| Paramètre | Valeur | Unité |
| :--- | :--- | :--- |
| **Hauteur Étage 0** | 0 | mm |
| **Hauteur Étage 1** | 170 | mm |
| **Hauteur Étage 2** | 336 | mm |
| **Résolution** | 350 | pas / mm |
| **Tolérance** | 10 | mm |

## 📡 Configuration & Build

Le projet est basé sur **Zephyr RTOS**.

### Pré-requis
* Zephyr SDK installé.
* West build tool.

### Commandes

```bash
# Compiler le projet pour la STM32F746G-DISCO
west build -p -b stm32f746g_disco

# Flasher la carte
west flashn --runner openocd


