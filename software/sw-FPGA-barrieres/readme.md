# 🚧 Contrôleur de Barrière FPGA (SoC RISC-V)

![Status](https://img.shields.io/badge/Status-Stable-success)
![Platform](https://img.shields.io/badge/Platform-Nexys_A7--100T-orange)
![Arch](https://img.shields.io/badge/Arch-RISC--V_32-red)
![OS](https://img.shields.io/badge/OS-Linux_Buildroot-yellow)

## 📖 Description

Ce module contient le logiciel embarqué tournant sur le processeur softcore (VexRiscv) implémenté dans le FPGA. Il fait le lien entre le monde IoT (commandes MQTT via Ethernet) et le hardware (Drivers moteurs physiques).

Le programme interagit avec les registres matériels des contrôleurs de moteurs pas-à-pas via **Memory Mapped I/O (MMIO)** et s'abonne au broker MQTT pour recevoir les ordres d'ouverture/fermeture.

---

## ⚡ Démarrage Automatique (Autorun)

Le système est conçu pour être autonome. Une fois le bitstream (Gateware) chargé sur la FPGA, le SoC démarre et cherche un système de fichiers sur la carte SD.

**Dossier :** `gateware/fpga/sd-image/`

### Préparation de la Carte SD
1. **Compilation (si modification du code C) :**
   Assurez-vous que le binaire `v4` à jour est présent dans le dossier image.
   ```bash
   # Exemple de copie après compilation
   cp software/sw-FPGA-barrieres/v4 gateware/fpga/sd-image/
   ```

2. **Copie sur SD :**
   * Formater la carte SD en **FAT32**.
   * Copier l'intégralité du contenu du dossier `gateware/fpga/sd-image/` à la racine de la carte.

3. **Lancement :**
   * Insérer la carte dans le slot de la Nexys A7.
   * Charger le bitstream via Vivado.
   * Le système démarre automatiquement.

> **Mécanisme :** Le fichier `startup.sh` présent à la racine est exécuté automatiquement au boot de Linux. Il configure le réseau et lance le binaire `v4` avec la configuration par défaut.
---
## 🛠 Compilation (Cross-Compile)

Le code C ne peut pas être compilé avec le `gcc` de votre PC (x86), il doit être compilé pour l'architecture RISC-V cible.

**Pré-requis :** Toolchain Buildroot générée.

```bash
# Exemple de commande de compilation pour la version finale (v4)
~/parking_fpga/buildroot/output/host/bin/riscv32-buildroot-linux-gnu-gcc \
    src/v4-run-multiple.c \
    -o bin/v4 \
    -march=rv32ima \
    -mabi=ilp32 \
    -lmosquitto
```

* `-lmosquitto` : Link avec la librairie client MQTT.
* `-march=rv32ima` : Architecture RISC-V 32-bits (Integer, Multiply, Atomic).

---

## 📜 Historique des Versions

Le développement du driver a suivi une approche itérative, passant d'un test simple à un gestionnaire multi-barrières robuste.

### v0 : Version Initiale (Preuve de Concept)
* **Fichier :** `v0-test-concept.c`
* **Fonctionnalité :** Contrôle une seule barrière à l'adresse hardcodée `0xF0000000`.
* **Logique :** Séquence de rotation fixe (tableaux statiques). Bloque l'exécution pendant le mouvement.
* **MQTT :** Topic global simple `parking/barrier`.

### v1 : Gestion des IDs et du Sens (Soft)
* **Fichier :** `v1-ids-sens.c`
* **Nouveauté :** Introduction des arguments CLI (`./v1 [ID]`).
* **Topics Dynamiques :** `parking/barrier_{ID}/state`.
* **Inversion Logique :** Ajout du paramètre "Sens" pour compenser le montage physique (Moteur à gauche ou à droite) sans recâblage.
* *Limite :* Pilote toujours la même adresse physique, quel que soit l'ID.

### v2 : Mode Calibration & Test
* **Fichier :** `v2-configuration.c`
* **Objectif :** Outil de diagnostic pour déterminer le nombre de pas exact pour 90°.
* **Mode RAW :** Pas d'état "Ouvert/Fermé", mais des commandes directes de pas via MQTT (`parking/test`).
    * `p64` : 64 pas sens Positif.
    * `m128` : 128 pas sens Minus.
* **Résultat :** A permis de fixer la constante `CYCLES_REQUIRED = 128`.

### v3 : Support Multi-Adresses (Hardware)
* **Fichier :** `v3-multiple-adress.c`
* **Nouveauté :** Mapping réel des adresses physiques.
* **Table de Mapping :** Associe un ID logiciel (0, 1...) à une adresse AXI physique (`0xF0000000`, `0xF0000800`...).
* **Usage :** Nécessite de lancer une instance du programme par barrière physique.

### 🌟 v4 : Architecture Unifiée (Finale)
* **Fichier :** `v4-run-multiple.c`
* **Architecture :** Gestionnaire unique (Single Process) pour tout le parking.
* **Optimisation :** Une seule connexion MQTT partagée. Structure C objet (`struct Barrier`) pour isoler les états.
* **CLI Avancée :** Configuration au lancement sous la forme `ID:SENS`.
    * Exemple : `./v4 0:1 2:0` (Lance Barrière 0 en sens inversé et Barrière 2 en sens normal).
* **Déploiement :** C'est cette version qui est lancée par le `startup.sh`.

---

## 📡 Utilisation MQTT

Pour piloter une barrière depuis le réseau (ou la BeagleBone) :

```bash
# Ouvrir la barrière 0
mosquitto_pub -h 192.168.78.2 -t "parking/barrier_0/state" -m "OPEN"

# Fermer la barrière 0
mosquitto_pub -h 192.168.78.2 -t "parking/barrier_0/state" -m "CLOSE"
