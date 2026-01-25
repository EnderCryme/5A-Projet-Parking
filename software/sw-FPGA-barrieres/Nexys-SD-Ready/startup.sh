#!/bin/sh

echo "--- Démarrage du script utilisateur SD ---"

# 1. Configuration IP
echo "Configuring Ethernet..."
ifconfig eth0 192.168.1.50 netmask 255.255.255.0 up

# 2. Exécution de ton programme v3
# Note: La carte SD est déjà montée dans /mnt/sd par le script pont
if [ -f /mnt/sd/v4 ]; then
    echo "Lancement de v4..."
    # On rend v3 executable si besoin
    chmod +x /mnt/sd/v4
    # On le lance
    /mnt/sd/v4 0:1 1:0
else
    echo "Erreur : v4 introuvable !"
fi

echo "--- Fin du script utilisateur ---"