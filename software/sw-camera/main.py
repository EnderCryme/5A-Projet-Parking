import threading
import time
import sqlite3
from flask import Flask, Response, jsonify
from datetime import datetime

from src.lcd_manager import LcdManager
from src.sensor_manager import SensorManager
from src.db_manager import DbManager
from src.mqtt_manager import MqttManager
from src.camera_manager import CameraManager

# --- CONFIGURATION ---
CAM_ENTRY_ID = 1
CAM_EXIT_ID = 3
SENSOR_CS = 1
LCD_CS = 0
DB_PATH = "/home/vcauq/parking.db"

app = Flask(__name__)

lcd = None
sensor = None
db = None
mqtt = None
cam_entry = None
cam_exit = None

lcd_lock = threading.Lock()

def on_plate_detected(plaque, role):
    print(f"\n[MAIN] 🚗 Plaque : {plaque} (Zone: {role})")
    
    # On gère la base de données et MQTT en silence
    msg_ecran = ""
    if role == "entry":
        msg_ecran = db.process_entree(plaque)
        mqtt.publish("entree", f"{plaque}|{msg_ecran}")
    else:
        msg_ecran = db.process_sortie(plaque)
        mqtt.publish("sortie", f"{plaque}|{msg_ecran}")

    # On lance l'affichage spécifique (Plaque ou Plaque + Au Revoir)
    threading.Thread(target=afficher_scenario_lcd, args=(plaque, role)).start()

def afficher_scenario_lcd(plaque, role):
    """Gère l'affichage selon le scénario exact demandé"""
    with lcd_lock:
        try:
            lcd.clear()
            
            # 1. On affiche TOUJOURS la plaque en défilement
            lcd.scroll_text(plaque)
            time.sleep(0.5)

            # 2. Si c'est la SORTIE, on ajoute "AU REVOIR"
            if role == "exit":
                lcd.scroll_text("AU REVOIR")
                time.sleep(0.5)
            
            # Et HOP ! Le 'with lcd_lock' se termine et la boucle reprend
            lcd.clear()
        except: pass

def boucle_physique():
    """Boucle d'attente (Bienvenue / Heure / Temp)"""
    print("[SYSTEM] Démarrage boucle LCD...")
    while True:
        try:
            # 1. BIENVENUE (Défilement)
            with lcd_lock:
                lcd.clear()
                lcd.scroll_text("   BIENVENUE   ")
            time.sleep(1)

            # 2. HEURE (Fixe)
            with lcd_lock:
                lcd.clear()
                now = datetime.now()
                lcd.afficher_texte_fixe(now.strftime("%H:%M"))
            time.sleep(4) 
            
            # 3. TEMPÉRATURE (Fixe)
            if sensor:
                temp = sensor.get_temperature()
                if temp is not None:
                    with lcd_lock:
                        lcd.clear()
                        lcd.afficher_texte_fixe(f"{temp}C")
                    time.sleep(4)
            
            time.sleep(1)

        except Exception:
            time.sleep(5)

# --- ROUTES WEB ---
@app.route('/')
def index():
    return """
    <body style='background:#222; text-align:center; color:white; font-family:sans-serif; margin-top:30px'>
    <h1>🅿️ PARKING BEAGLEBONE</h1>
    <div style='display:flex; justify-content:center; gap:20px; flex-wrap:wrap'>
        <div style='background:#333; padding:10px; border-radius:10px'>
            <h2 style='color:#0f0'>CAMÉRA ENTRÉE</h2>
            <img src='/vid_in' style='border:4px solid #0f0; width:480px; height:360px; background:black'>
        </div>
        <div style='background:#333; padding:10px; border-radius:10px'>
            <h2 style='color:#f00'>CAMÉRA SORTIE</h2>
            <img src='/vid_out' style='border:4px solid #f00; width:480px; height:360px; background:black'>
        </div>
    </div>
    <br><br>
    <a href='/api/json' target='_blank' style='color:cyan; font-size:20px'>HISTORIQUE JSON</a>
    </body>
    """

@app.route('/vid_in')
def vid_in(): 
    return Response(cam_entry.generate_jpeg(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/vid_out')
def vid_out(): 
    return Response(cam_exit.generate_jpeg(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/json')
def get_json():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM historique ORDER BY id DESC LIMIT 20")
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except: return jsonify([])

if __name__ == '__main__':
    print("--- DÉMARRAGE TURBO ---")
    try:
        db = DbManager()
        mqtt = MqttManager()
        lcd = LcdManager(cs_pin=LCD_CS)
        sensor = SensorManager(cs_pin=SENSOR_CS)
    except Exception as e:
        print(f"⚠️ Erreur Matériel: {e}")

    try:
        cam_entry = CameraManager(CAM_ENTRY_ID, "entry", callback_detection=on_plate_detected)
        cam_entry.start()
        cam_exit = CameraManager(CAM_EXIT_ID, "exit", callback_detection=on_plate_detected)
        cam_exit.start()
    except Exception as e:
        print(f"❌ Erreur Caméras: {e}")

    threading.Thread(target=boucle_physique, daemon=True).start()

    print("SRV WEB: http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
