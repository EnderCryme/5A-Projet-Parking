Voici le contenu complet et fusionné pour le fichier `BMS_ADVANCED_CONFIG.md`. J'ai intégré le script Python dans une nouvelle section **"Outils d'Automatisation"** à la fin du document.

***

# ⚙️ BMS Advanced Configuration & Data Flash

Ce document détaille les registres avancés du **BQ40Z50**. Contrairement aux mesures temps-réel, ces paramètres sont stockés dans la **Data Flash** du composant. Ils définissent le comportement physique et les sécurités du BMS.

> [!WARNING]
> **Attention :** Modifier ces valeurs modifie le comportement de sécurité de la batterie.
> 1. Le dispositif doit être en mode **UNSEALED** (déverrouillé) pour accepter l'écriture.
> 2. Une mauvaise configuration peut empêcher l'ouverture des MOSFETs ou endommager les cellules.

---

## 🔐 1. Structure de la Mémoire (Data Flash)

Pour configurer le BMS, on n'utilise pas les commandes I2C simples, mais on écrit dans des "Classes" et "Sous-classes".
* **Protocole :** SMBus Block Write
* **Adresse I2C :** `0x0B` (Smart Battery)

### 🔋 Configuration du Pack (Design)

Ces registres définissent l'architecture physique de votre batterie (4S3P dans notre cas).

| Classe | Sous-classe | Offset | Nom | Description | Valeur Type (4S) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Settings** | Configuration | 0 | **DA Configuration** | Définit le nombre de cellules (Bitmask). | `0x00` (voir détail bas de page) |
| **Gas Gauging** | Design | 0 | **Design Capacity** | Capacité théorique du pack (mAh). | `10500` (3 x 3500mAh) |
| **Gas Gauging** | Design | 2 | **Design Energy** | Énergie théorique (cWh). | `1512` (151.2 Wh) |

### 🛡️ Sécurités & Protections (Safety)

Ces seuils déclenchent l'ouverture d'urgence des MOSFETs (Protection Matérielle).

| Protection | Registre (Class/Sub) | Nom | Seuil (Threshold) | Délai | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CUV** | Protections / Voltage | **CUV Threshold** | 2800 mV | 2 s | **Cell Under Voltage**. Arrêt décharge si une cellule < 2.8V. |
| **COV** | Protections / Voltage | **COV Threshold** | 4250 mV | 2 s | **Cell Over Voltage**. Arrêt charge si une cellule > 4.25V. |
| **OCC** | Protections / Current | **OCC Threshold** | 6000 mA | 2 s | **Over Current Charge**. Courant charge max. |
| **OCD1** | Protections / Current | **OCD1 Threshold** | 20000 mA | 2 s | **Over Current Discharge**. Courant décharge max (Tier 1). |
| **OTC** | Protections / Temp | **OTC Threshold** | 55°C | 2 s | **Over Temp Charge**. Trop chaud pour charger. |

---

## 💡 2. Configuration des Périphériques (LEDs & GPIO)

Le BQ40Z50 peut piloter une jauge à LED (jusqu'à 5 segments) directement si le PCB est câblé pour.

**Location :** `Settings` -> `Configuration` -> `LED Configuration`

| Paramètre | Bit / Valeur | Fonction |
| :--- | :--- | :--- |
| **LED_ON** | Bit 0 | Si `1`, active la gestion des LEDs lors de l'appui bouton. |
| **LED_BLINK** | Bit 2 | Si `1`, les LEDs clignotent pendant la charge. |
| **CHG_IND** | Bit 3 | Indication visuelle de charge. |
| **LED Check** | N/A | La jauge s'active si le courant > seuil défini (Threshold). |

---

## 🛠️ 3. Commandes "Manufacturer Access" (MAC)

Ce sont des commandes exécutables envoyées au registre `0x44` (Little Endian) pour forcer des actions immédiates sans programmer la flash.

| Commande MAC (`0x44`) | Nom | Action / Effet |
| :--- | :--- | :--- |
| **`0x0001`** | **Device Type** | Renvoie le modèle (ex: `0x4500` pour BQ40Z50). |
| **`0x0021`** | **Gauging** | Active/Désactive l'algo d'apprentissage (Impedance Track). |
| **`0x0022`** | **FET Control** | **Force manuelle** des MOSFETs (Debug uniquement). |
| **`0x0041`** | **Device Reset** | Redémarre le processeur du BMS (Soft Reset). |
| **`0x0010`** | **Shutdown** | Met le BMS en veille profonde (Consommation ~0µA). Réveil via tension chargeur. |
| **`0x0030`** | **Seal Device** | Verrouille le BMS (Lecture seule) pour la production. |

---

## 📝 Note Technique : Configuration Cellules (DA Config)

Le registre **DA Configuration** est le plus critique. Il indique au BMS combien de cellules sont en série.
Pour un système 4S (BeagleBone Project) :

*   **Registre :** `Settings.Configuration.DA Configuration`
*   **Adresse Flash :** 0x45CC (dépend version firmware)
*   **Format :**
    *   **CC0 (Bit 0)** : Cell Count 0
    *   **CC1 (Bit 1)** : Cell Count 1

| Cellules | CC1 | CC0 | Hex Value (approx) |
| :--- | :---: | :---: | :--- |
| **3 Cells** | 1 | 0 | `0x02` |
| **4 Cells** | 1 | 1 | `0x03` |

> **Note :** Si ce registre est mal configuré, le BMS mesurera une tension totale erronée et se mettra en sécurité immédiate.

---

## 🐍 4. Outil d'Automatisation (Script Python)

Ce script MicroPython pour le RP2350 permet de modifier la Data Flash (ex: changer la capacité design).

**Fonctionnement :**
1. **Unseal :** Envoie les clés de sécurité (`0x0414`, `0x3672`) pour déverrouiller l'écriture.
2. **Write Flash :** Écrit un bloc de données avec calcul du Checksum obligatoire.
3. **Reset :** Redémarre le BMS pour appliquer la nouvelle config.

```python
from machine import I2C, Pin
import time
import struct

# --- CONFIGURATION I2C (RP2350) ---
SDA_PIN = 8
SCL_PIN = 9
I2C_FREQ = 400000
BMS_ADDR = 0x0B

# --- EXEMPLE: ADRESSES DATA FLASH (BQ40Z50) ---
# SubClass 48 (Gas Gauging) / Offset 0 = Design Capacity
DF_CLASS_GAS_GAUGING = 48 
DF_OFFSET_DESIGN_CAP = 0 

# Commandes SMBus Flash Access
CMD_MAC      = 0x00
CMD_DF_CLASS = 0x3E
CMD_DF_BLOCK = 0x3F
CMD_DF_DATA  = 0x40
CMD_DF_CSUM  = 0x60

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN), freq=I2C_FREQ)

def bms_write_word_mac(command):
    """Ecrit une commande MAC en Little Endian"""
    payload = struct.pack('<H', command)
    i2c.writeto_mem(BMS_ADDR, CMD_MAC, payload)
    time.sleep(0.05)

def unseal_bms():
    """Déverrouille le BMS (Default Keys: 0x0414, 0x3672)"""
    print("🔓 UNSEAL BMS...")
    bms_write_word_mac(0x0414) # Key 1
    bms_write_word_mac(0x3672) # Key 2
    print("   -> Clés envoyées.")

def write_data_flash(class_id, offset, data_bytes):
    """Ecrit dans la Data Flash avec calcul de Checksum"""
    print(f"📝 Ecriture Flash | Class: {class_id}, Offset: {offset}")
    try:
        # 1. Setup Class & Block
        i2c.writeto_mem(BMS_ADDR, CMD_DF_CLASS, bytes([class_id]))
        i2c.writeto_mem(BMS_ADDR, CMD_DF_BLOCK, bytes([offset // 32]))
        
        # 2. Lire le bloc existant (32 bytes) pour ne pas corrompre le reste
        current_block = list(i2c.readfrom_mem(BMS_ADDR, CMD_DF_DATA, 32))
        
        # 3. Modifier les octets cibles
        local_idx = offset % 32
        for i, b in enumerate(data_bytes):
            if local_idx + i < 32:
                current_block[local_idx + i] = b
        
        # 4. Ecriture du nouveau bloc
        new_block_bytes = bytes(current_block)
        i2c.writeto_mem(BMS_ADDR, CMD_DF_DATA, new_block_bytes)
        
        # 5. Calcul et Envoi du Checksum (Spécifique TI)
        # Checksum = (255 - (Sum of (Class + Block + Data) % 256))
        total_sum = sum(new_block_bytes) + class_id + (offset // 32)
        checksum = (255 - (total_sum & 0xFF)) & 0xFF
        
        i2c.writeto_mem(BMS_ADDR, CMD_DF_CSUM, bytes([checksum]))
        print(f"   -> Succès ! Checksum: {hex(checksum)}")
        
    except Exception as e:
        print(f"❌ Erreur Flash : {e}")

def reset_bms():
    """Soft Reset du BMS pour recharger la Flash"""
    print("🔄 Reset BMS...")
    bms_write_word_mac(0x0041)

# --- MAIN SEQUENCE ---
if __name__ == "__main__":
    unseal_bms()
    time.sleep(1)
    
    # Exemple: Set Capacity = 10500 mAh (0x2904)
    # write_data_flash(DF_CLASS_GAS_GAUGING, DF_OFFSET_DESIGN_CAP, [0x04, 0x29])
    
    # reset_bms()
```
