from machine import Pin, I2C
import time
import ssd1306

# ================= CONFIGURATION I2C (RP2350) =================
# KICAD : SDA=GPIO8, SCL=GPIO9 
i2c = I2C(0, sda=Pin(8), scl=Pin(9), freq=400000)

BMS_ADDRESS = 0x0B      # Adresse du BQ40z50 
OLED_ADDRESS = 0x3C     # Adresse de l'écran OLED 

# Registres standard SMBus (Smart Battery Data)
CMD_TEMP = 0x08     # Température (0.1°K)
CMD_VOLT = 0x09     # Tension (mV)
CMD_CURR = 0x0A     # Courant (mA)
CMD_SOC  = 0x0D     # État de charge (%)

# ================= INITIALISATION ÉCRAN =================
ecran_actif = False
try:
    # Initialisation de l'écran 128x64
    oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=OLED_ADDRESS)
    ecran_actif = True
    print("OLED OK")
except Exception as e:
    print("Erreur écran:", e)

# ================= FONCTIONS =================

def lire_word(registre):
    """Lit 2 octets sur le BMS (Format Little Endian pour SMBus)"""
    try:
        data = i2c.readfrom_mem(BMS_ADDRESS, registre, 2)
        # Conversion bytes -> unsigned short (Little Endian)
        return data[0] | (data[1] << 8)
    except:
        return None

def convertir_signe(val):
    """Gère les nombres négatifs (Complément à 2 sur 16 bits)"""
    if val is None: return 0
    if val > 32767:
        return val - 65536
    return val

def get_bms_data():
    """Récupère et convertit toutes les données"""
    raw_v = lire_word(CMD_VOLT)
    raw_i = lire_word(CMD_CURR)
    raw_s = lire_word(CMD_SOC)
    raw_t = lire_word(CMD_TEMP)

    # Tension : mV -> V
    volts = raw_v / 1000.0 if raw_v is not None else 0.0
    
    # Courant : mA -> A (et gestion du signe)
    amperes = convertir_signe(raw_i) / 1000.0 if raw_i is not None else 0.0
    
    # SOC : %
    soc = raw_s if raw_s is not None else 0
    
    # Température : 0.1°K -> °C
    temp_c = (raw_t * 0.1) - 273.15 if raw_t is not None else 0.0

    return volts, amperes, soc, temp_c

# ================= BOUCLE PRINCIPALE =================

while True:
    v, i, soc, t = get_bms_data()
    
    # Affichage Console
    print("U: {:.2f}V | I: {:.3f}A | Batt: {}% | T: {:.1f}C".format(v, i, soc, t))

    # Affichage Écran
    if ecran_actif:
        oled.fill(0) # Efface l'écran
        oled.rect(0, 0, 128, 64, 1) # Cadre
        
        oled.text("BMS BQ40Z50", 20, 4)
        oled.text("{:.2f} V".format(v), 5, 18)
        oled.text("{:.1f} C".format(t), 80, 18)
        oled.text("{:.3f} A".format(i), 5, 30)
        oled.text("Charge: {}%".format(soc), 5, 42)
        
        # Barre de progression
        oled.rect(5, 54, 118, 6, 1) # Contour barre
        bar_width = int((soc / 100) * 114)
        oled.fill_rect(7, 56, bar_width, 2, 1) # Remplissage
        
        oled.show()

    time.sleep(1)