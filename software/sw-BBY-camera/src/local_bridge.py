import cv2
import paho.mqtt.client as mqtt
import json
import time
import threading
from src.lcd_manager import LcdManager
from src.sensor_manager import SensorManager

# CONFIGURATION DU PONT
BROKER_ADDRESS = "broker.hivemq.com" # Broker public pour l'exemple (ou ton serveur privé)
PORT = 1883
PARKING_ID = "parking_lyon_01" # Identifiant unique si tu as plusieurs parkings

# INIT MATERIEL LOCAL
lcd = LcdManager(cs_pin=0)
sensor = SensorManager(cs_pin=1)

# --- 1. GESTION MQTT (LE LIEN) ---
def on_connect(client, userdata, flags, rc):
    print("✅ Connecté au Cloud via MQTT")
    # On écoute les ordres venant du Cloud (Ouvrir barrière, Afficher message)
    client.subscribe(f"{PARKING_ID}/cmd/#")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode()
        
        # ORDRE: OUVRIR BARRIÈRE
        if "barrier" in topic:
            action = payload # "OPEN" / "CLOSE"
            print(f"⚡ Action Barrière physique: {action}")
            # Ici on activerait le GPIO moteur
            
        # ORDRE: MESSAGE LCD
        elif "lcd" in topic:
            lcd.clear()
            lcd.scroll_text(payload)
            
    except Exception as e: print(f"Erreur commande: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER_ADDRESS, PORT, 60)
client.loop_start()

# --- 2. INTELLIGENCE LOCALE (IA / CAMERA) ---
# On garde l'IA ici pour ne pas saturer la bande passante internet
def smart_loop():
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret: continue
        
        # ... (Code de détection de plaque existant) ...
        # Imaginons qu'on détecte une plaque :
        plaque_detectee = "AA-123-BB" 
        
        if plaque_detectee:
            print(f"🚀 Plaque {plaque_detectee} envoyée au Cloud")
            
            # ON DEMANDE AU CLOUD SI ON PEUT OUVRIR
            payload = json.dumps({
                "plaque": plaque_detectee,
                "timestamp": time.time(),
                "camera_id": "cam_in"
            })
            client.publish(f"{PARKING_ID}/event/detection", payload)
            
            # OPTIONNEL : Envoi d'une photo (Snapshot) au lieu du flux vidéo continu
            # C'est la méthode pro pour éviter la latence vidéo sur internet
            _, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            client.publish(f"{PARKING_ID}/event/snapshot", jpg_as_text)

        time.sleep(0.1)

# --- 3. BOUCLE CAPTEURS ---
def sensor_loop():
    while True:
        temp = sensor.get_temperature()
        # On envoie la télémétrie au cloud toutes les 30s
        client.publish(f"{PARKING_ID}/telemetry/temp", temp)
        time.sleep(30)

# LANCEMENT
threading.Thread(target=smart_loop).start()
threading.Thread(target=sensor_loop).start()