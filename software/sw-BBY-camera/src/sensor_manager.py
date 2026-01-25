import time
import random

# ==========================================
# GESTION SIMULATION (WINDOWS vs LINUX)
# ==========================================
try:
    import spidev
    from adafruit_bme680 import Adafruit_BME680_SPI
    IS_REAL_HARDWARE = True
except ImportError:
    IS_REAL_HARDWARE = False
    # On mock spidev pour que les classes techniques ne plantent pas à la définition
    class MockSpi:
        def open(self, bus, device): pass
        def max_speed_hz(self, speed): pass
        def mode(self, mode): pass
        def xfer2(self, data): return [0]*len(data)
        def close(self): pass
    spidev = type('obj', (object,), {'SpiDev': MockSpi})
    
    # On crée une fausse classe BME680 pour éviter les NameError
    class Adafruit_BME680_SPI: pass

# ==========================================
# 1. CLASSES TECHNIQUES (Smart-SPI)
# ==========================================
class Smart_SPI_Adapter:
    def __init__(self, cs_pin):
        self.spi = spidev.SpiDev()
        self.spi.open(0, cs_pin)
        
        # Réglages pour stabilité maximale
        self.spi.max_speed_hz = 50000 
        self.spi.mode = 3 
        
        self.pending_write = None 

    def try_lock(self): return True
    def unlock(self): pass
    def configure(self, baudrate=100000, polarity=0, phase=0, bits=8): pass

    def write(self, buf, start=0, end=None):
        if end is None: end = len(buf)
        self.pending_write = list(buf[start:end])

    def readinto(self, buf, start=0, end=None, write_value=0):
        if end is None: end = len(buf)
        length = end - start
        
        tx_buffer = []
        if self.pending_write:
            tx_buffer.extend(self.pending_write)
            self.pending_write = None
        
        tx_buffer.extend([write_value] * length)
        rx_buffer = self.spi.xfer2(tx_buffer)
        
        response = rx_buffer[-length:]
        for i in range(length):
            buf[start + i] = response[i]

class FakeCS:
    def __init__(self, adapter): 
        self.adapter = adapter
    def switch_to_output(self, value=True): pass
    def switch_to_input(self): pass
    @property
    def value(self): return True
    @value.setter
    def value(self, val):
        if val and self.adapter.pending_write:
            self.adapter.spi.xfer2(self.adapter.pending_write)
            self.adapter.pending_write = None

# ==========================================
# 2. MANAGER PRINCIPAL
# ==========================================
class SensorManager:
    def __init__(self, cs_pin=1):
        self.cs_pin = cs_pin
        self.sensor = None
        self.adapter = None
        self.offset = -5 
        self.init_sensor()

    def init_sensor(self):
        # --- MODE SIMULATION ---
        if not IS_REAL_HARDWARE:
            print("[SENSOR] ℹ️ Mode Simulation activé (Valeurs aléatoires)")
            self.sensor = "MOCK_SENSOR" # Juste pour dire qu'il est "là"
            return
        # -----------------------

        print(f"[SENSOR] Init Smart-SPI (Mode 3) sur CS{self.cs_pin}...")
        try:
            self.adapter = Smart_SPI_Adapter(self.cs_pin)
            cs_fake = FakeCS(self.adapter)
            self.sensor = Adafruit_BME680_SPI(self.adapter, cs_fake)
            self.sensor.sea_level_pressure = 1013.25
            
            print("[SENSOR] Préchauffage pour éliminer les valeurs 193°C...")
            for i in range(3):
                try:
                    _ = self.sensor.temperature
                    time.sleep(0.5) 
                except:
                    pass

            print("[SENSOR] ✅ OK (Prêt)")
        except Exception as e:
            print(f"[SENSOR] ❌ Erreur: {e}")
            self.sensor = None

    def get_temperature(self):
        # --- SIMULATION ---
        if not IS_REAL_HARDWARE:
            return round(random.uniform(19.0, 24.0), 1)
        # ------------------

        if not self.sensor: return None
        try:
            temp = self.sensor.temperature + self.offset
            if temp > 100 or temp < -50:
                return None
            return round(temp, 1)
        except: return None

    def get_humidity(self):
        # --- SIMULATION ---
        if not IS_REAL_HARDWARE:
            return round(random.uniform(40.0, 60.0), 1)
        # ------------------

        if not self.sensor: return None
        try:
            return round(self.sensor.humidity, 1)
        except: return None

    def close(self):
        if IS_REAL_HARDWARE and self.adapter and hasattr(self.adapter, 'spi'):
            self.adapter.spi.close()