# Système d'Accès Parking Automatisé (STM32 Node)

![Status](https://img.shields.io/badge/Status-Prototype-yellow)
![Platform](https://img.shields.io/badge/Platform-STM32F746G--DISCO-blue)
![OS](https://img.shields.io/badge/OS-Zephyr%20RTOS-green)
![GUI](https://img.shields.io/badge/GUI-LVGL-orange)

## 📖 Description du Projet

Ce dépôt contient le firmware du sous-système d'interface et de gestion d'accès pour un parking automatisé. Le système repose sur une architecture IoT distribuée où ce module STM32 agit comme un **nœud de périphérie (Edge Node)** intelligent.

Il assure l'interface homme-machine, l'acquisition des données environnementales en temps réel et la sécurité physique de l'accès (Anti-Tailgating) avant de communiquer avec le serveur central (BeagleBoard) via MQTT sur Ethernet.

### 🚀 Fonctionnalités Clés

* **Identification RFID (SPI) :** Lecture de badges Mifare via module RC522.
* **Interface Tactile (LVGL) :** IHM interactive avec rotation logicielle (180°) pour adaptation mécanique.
* **Gestion Éclairage (GPIO) :** Pilotage automatique via capteur de luminosité et relais de puissance.
* **Sécurité Active :** Algorithme "Anti-Tailgating" pour prévenir la fraude au passage barrière.
* **Mode Maintenance :** Badge Administrateur (`UID: AA63F605`) pour gestion locale (Ajout/Suppr clients).
* **Communication IoT :** Client MQTT asynchrone pour la télémétrie et le contrôle distant.

## 🛠 Architecture Matérielle

* **MCU :** STM32F746NG (Arm Cortex-M7)
* **Board :** STM32F746G-DISCO
* **Affichage :** LCD 4.3" (480x272) capacitif
* **Réseau :** Ethernet (RJ45)

### Pinout & Connexions (Overlay)

| Périphérique | Pin STM32 | Type | Description |
| :--- | :--- | :--- | :--- |
| **RFID RC522** | SPI2 Bus | SPI | Lecteur de badges 13.56MHz |
| **RFID CS** | `PA8` | GPIO Out | Chip Select RFID |
| **Capteur Prox** | `PI0` | GPIO In | Détection présence véhicule (Actif High) |
| **Capteur Lum** | `PH6` | GPIO In | Photorésistance (Actif Low) |
| **Relais LED** | `PI3` | GPIO Out | Commande éclairage puissance 12V |
| **Backlight** | `PK3` | GPIO Out | Rétroéclairage LCD (Eco-mode) |

## 📡 API MQTT

Le système communique sur le réseau local configuré tel que :
Broker @ 192.168.78.2, STM32 @ 192.168.78.3

| Topic | Direction | Payload | Description |
| :--- | :--- | :--- | :--- |
| `RFID/ID` | Pub (Out) | `[UID]` | Envoi de l'UID scanné au serveur. |
| `RFID/PRESENCE` | Pub (Out) | `0` / `1` | État du capteur de présence véhicule. |
| `RFID/CMD` | Sub (In) | `UNLOCK`/`DENY` | Réponse du serveur (Accès autorisé/refusé). |
| `parking/barrier_0/state` | Pub/Sub | `OPEN`/`CLOSE` | Commande directe de la barrière physique. |

## ⚙️ Configuration & Build

Le projet est basé sur **Zephyr OS**.

### Pré-requis
* Zephyr SDK installé.
* West build tool.

### Commandes de Build

```bash
# Compilation propre pour la cible disco
west build -p always -b stm32f746g_disco

# Flashage sur la carte
west flash

