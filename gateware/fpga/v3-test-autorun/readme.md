---

# Mise en place de l'Autorun (SD Card)

Configuration du Linux pour qu'il exécute automatiquement un script modifiable (`startup.sh`) situé sur la carte SD au démarrage.

**Avantage :** Cette méthode permet de modifier la configuration réseau ou les programmes à lancer **sans jamais avoir à recompiler le noyau ou le rootfs**. Il suffit d'éditer un fichier texte sur la carte SD depuis un PC ou même de le transférer depuis **le réseau** !

---

## Architecture

1. **Côté Système (Interne/Fixe) :** Un script "Pont" (`S99autorun`) est intégré dans l'image `rootfs.cpio`. Il se lance à la fin du boot, monte la carte SD et cherche le script utilisateur.
2. **Côté Utilisateur (Externe/Modifiable) :** Un script `startup.sh` est placé à la racine de la carte SD. Il contient vos commandes (IP, lancement d'app, etc.).

---

## Partie 1 : Installation du "Pont" (À faire une seule fois)

Cette étape modifie l'image du système de fichiers pour qu'elle sache lire la carte SD au démarrage.

### 1. Créer le script d'initialisation

Sur votre PC de développement, allez dans le dossier cible de Buildroot :

```bash
cd buildroot/output/target/etc/init.d/
```

Créez le fichier **`S99autorun`** :

```bash
nano S99autorun
```

Copiez-y le contenu suivant :

```bash
#!/bin/sh
# /etc/init.d/S99autorun
# Script de pont : Monte la SD et lance startup.sh s'il existe.

SD_MOUNT_POINT="/mnt/sd"
SD_DEVICE="/dev/mmcblk0p1"
USER_SCRIPT="startup.sh"

echo "[Autorun] Checking for SD Card..."

# 1. Créer le dossier de montage
mkdir -p $SD_MOUNT_POINT

# 2. Monter la partition FAT32 de la SD
mount $SD_DEVICE $SD_MOUNT_POINT

# 3. Vérifier et exécuter le script utilisateur
if [ -f "$SD_MOUNT_POINT/$USER_SCRIPT" ]; then
    echo "[Autorun] Found $USER_SCRIPT, executing..."
    
    # Force les droits d'exécution (utile si système de fichiers FAT)
    chmod +x "$SD_MOUNT_POINT/$USER_SCRIPT"
    
    # Exécution du script
    /bin/sh "$SD_MOUNT_POINT/$USER_SCRIPT"
else
    echo "[Autorun] No $USER_SCRIPT found on SD card."
fi
```

### 2. Rendre le script exécutable

C'est indispensable pour que Linux le lance au boot :

```bash
chmod +x S99autorun
```

### 3. Recompiler le Rootfs

Revenez à la racine du dossier `buildroot` et régénérez l'image :

```bash
cd ../../../..  # Retour racine buildroot
make
```

Le nouveau fichier **`rootfs.cpio`** (situé dans `output/images/`) contient maintenant le pont. Copiez-le sur votre carte SD.

---

## Partie 2 : Utilisation (Script modifiable)

Cette étape se fait directement sur la carte SD. Vous pouvez modifier ce fichier à volonté depuis Windows ou Linux.

### 1. Créer le script utilisateur

À la racine de la carte SD, créez un fichier nommé **`startup.sh`**.

### 2. Exemple de contenu

Voici un template pour configurer l'Ethernet et lancer un binaire `v3`.

```bash
#!/bin/sh

echo "--------------------------------"
echo "   Démarrage Script Utilisateur "
echo "--------------------------------"

# --- Configuration Réseau ---
echo "Configuration de l'IP..."
ifconfig eth0 192.168.1.50 netmask 255.255.255.0 up

# Optionnel : Ping pour vérifier
# ping -c 1 192.168.1.100

# --- Lancement de l'Application ---
APP_PATH="/mnt/sd/v3"

if [ -f "$APP_PATH" ]; then
    echo "Lancement de l'application v3..."
    chmod +x "$APP_PATH"
    "$APP_PATH"
else
    echo "ERREUR : Le programme v3 est introuvable sur la SD !"
fi

echo "--------------------------------"
echo "   Fin du Script Utilisateur    "
echo "--------------------------------"
```

---

## Dépannage

* **Le script ne se lance pas ?**
* Vérifiez que le fichier sur la SD s'appelle bien `startup.sh` (attention aux extensions masquées sous Windows, type `startup.sh.txt`).
* Vérifiez que vous avez bien copié le **nouveau** `rootfs.cpio` sur la carte SD.


* **Erreur "Permission denied" ?**
* Le script `S99autorun` inclut une commande `chmod +x` automatique, mais assurez-vous que votre binaire (`v3`) est bien compilé pour l'architecture RISC-V.


* **Erreur de montage SD ?**
* Assurez-vous que la carte SD est formatée en **FAT32** et que c'est la première partition (`mmcblk0p1`).
