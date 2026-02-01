
# Guide d'Installation et de Configuration

Ce document détaille les étapes techniques pour compiler le système d'exploitation (Buildroot), configurer le réseau pour MQTT et lancer l'application de contrôle de barrière sur le SoC LiteX/VexRiscv.

---

## 1. Génération du Système (Buildroot)

Nous devons générer une image Linux (Rootfs + Kernel) adaptée à l'architecture exacte du processeur VexRiscv configuré sur le FPGA.

### A. Configuration (`defconfig`)

Créez ou écrasez le fichier de configuration `configs/litex_vexriscv_defconfig` avec les paramètres suivants. Cette configuration active le support MQTT et ajuste le jeu d'instructions RISC-V.

```bash
cat > configs/litex_vexriscv_defconfig <<EOF
# --- ARCHITECTURE (STRICTE rv32ima) ---
BR2_riscv=y
BR2_RISCV_32=y

# Architecture manuelle pour correspondre au FPGA
BR2_RISCV_ISA_CUSTOM_RVI=y
BR2_RISCV_ISA_CUSTOM_RVM=y
BR2_RISCV_ISA_CUSTOM_RVA=y
# DÉSACTIVATION des extensions non supportées (Vital pour éviter SIGILL)
# BR2_RISCV_ISA_CUSTOM_RVC is not set
# BR2_RISCV_ISA_CUSTOM_RVF is not set
# BR2_RISCV_ISA_CUSTOM_RVD is not set

# ABI : On force les entiers (Soft Float)
BR2_RISCV_ABI_ILP32=y

# --- SYSTEME ---
BR2_TARGET_GENERIC_HOSTNAME="litex-c"
BR2_TARGET_GENERIC_ISSUE="Welcome to LiteX (C Version)"
BR2_SYSTEM_DHCP="eth0"
BR2_TARGET_ROOTFS_CPIO=y

# --- PAQUETS ---
# MQTT (Indispensable pour le projet)
BR2_PACKAGE_MOSQUITTO=y
BR2_PACKAGE_MOSQUITTO_BROKER=y
BR2_PACKAGE_MOSQUITTO_CLIENT=y

# Editeur de texte (Pratique pour débugger)
BR2_PACKAGE_NANO=y
EOF

```

### B. Compilation

Lancez la génération de l'image (cela peut prendre du temps la première fois) :

```bash
make litex_vexriscv_defconfig
make clean
make

```

> **⚠️ Note pour les utilisateurs WSL :**
> Si vous rencontrez l'erreur : `Your PATH contains spaces, TABs, and/or newline (\n) characters.`, vous devez nettoyer votre variable PATH avant de compiler :
> ```bash
> export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
> 
> ```
> 
> 

---

## 2. Configuration Réseau (Windows / WSL)

Si votre Broker MQTT (Mosquitto) tourne sur votre PC de développement (Windows ou WSL) et que vous souhaitez que le FPGA s'y connecte via Ethernet, vous devez autoriser le trafic entrant.

Ouvrez un terminal (PowerShell ou CMD) en mode **Administrateur** et exécutez la commande suivante pour rediriger le port 1883 :

```powershell
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=1883 connectaddress=<IP_DE_VOTRE_PC> connectport=1883

```

*Remplacez `<IP_DE_VOTRE_PC>` par l'adresse IP de votre machine sur le réseau local.*

---

## 3. Déploiement de l'Application (v4)

Une fois le FPGA démarré sous Linux, transférez le fichier source `v4.c` (via SCP, carte SD, ou copier-coller avec `nano`).

### Compilation sur la cible

Utilisez `gcc` (fourni par Buildroot) pour compiler le programme en liant la bibliothèque Mosquitto :

```bash
gcc v4.c -o v4 -lmosquitto

```

### Utilisation

Le programme `v4` est un gestionnaire unifié. Vous devez spécifier quelles barrières activer et leur configuration initiale.

**Syntaxe :** `./v4 <ID> <ID:SENS> ...`

* `ID` : Numéro de la barrière (0 à 3).
* `SENS` (Optionnel) : `0` pour Normal, `1` pour Inversé.

**Exemples :**

1. **Activer les barrières 0 et 1 en mode normal :**
```bash
./v4 0 1

```


2. **Activer la barrière 0 en inversé et la 2 en normal :**
```bash
./v4 0:1 2:0

```