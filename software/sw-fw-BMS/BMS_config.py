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
