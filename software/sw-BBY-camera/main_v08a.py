import cv2
import pytesseract
import threading
import time
import re
import numpy as np
import os
import json
import hashlib
from datetime import datetime, timedelta
from collections import Counter
from flask import Flask, Response, jsonify, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import paho.mqtt.client as mqtt_client

# --- IMPORT MODULES CUSTOM ---
# Assurez-vous que le dossier 'src' contient bien db_manager.py, lcd_manager.py, sensor_manager.py
from src.db_manager import DbManager, User
from src.lcd_manager import LcdManager
from src.sensor_manager import SensorManager

# --- CONFIGURATION ---
CAM_ENTRY = 0 # Modifier l'index si nécessaire (ex: 0 ou 1)
CAM_EXIT = 2  # Modifier l'index si nécessaire
DB_PATH = "parking.db"
SAMPLES_TO_TAKE = 3 
LCD_CS = 0
SENSOR_CS = 1
RFID_TIMEOUT = 15.0 

app = Flask(__name__)
app.secret_key = 'SECRET_KEY_PRODUCTION_PARKING' # Changez ceci pour la sécurité

# --- VARIABLES GLOBALES ---
last_rfid_unlock = 0 
lcd = None
sensor = None
db = None 
mqtt = None
lcd_lock = threading.Lock()
mqtt_logs = [] # Logs pour le dashboard web

# ==========================================
# 1. INITIALISATION SYSTÈME
# ==========================================

# DB & LOGIN
db = DbManager(DB_PATH)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.get_user_by_id(user_id)

# MATÉRIEL (Try/Except pour éviter le crash si pas de GPIO)
print("--- INIT MATERIEL ---")
try:
    lcd = LcdManager(cs_pin=LCD_CS)
    sensor = SensorManager(cs_pin=SENSOR_CS)
    print("✅ LCD & Capteurs OK")
except Exception as e: 
    print(f"⚠️ Mode Simulation (Pas de GPIO): {e}")

# ==========================================
# 2. GESTION MQTT
# ==========================================
class MqttHandler:
    def __init__(self, db_manager):
        self.client = mqtt_client.Client()
        self.db = db_manager
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        try:
            self.client.connect("localhost", 1883, 60)
            self.client.loop_start()
            print("✅ MQTT Connecté")
        except: print("⚠️ Erreur Connexion MQTT")

    def on_connect(self, client, userdata, flags, rc):
        client.subscribe("RFID/#")
        client.subscribe("parking/#") 

    def on_message(self, client, userdata, msg):
        global last_rfid_unlock, mqtt_logs
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8")
            
            # Logging pour le web
            t = datetime.now().strftime("%H:%M:%S")
            mqtt_logs.insert(0, f"[{t}] {topic} : {payload}")
            if len(mqtt_logs) > 30: mqtt_logs.pop()

            # Logique RFID
            if topic == "RFID/ID":
                print(f"[RFID] Scan: {payload}")
                nom = self.db.verifier_badge(payload)
                if nom:
                    print(f"   => ACCES AUTORISÉ ({nom})")
                    last_rfid_unlock = time.time()
                    client.publish("parking/RFID/CMD", "UNLOCK_READY") 
                else:
                    client.publish("parking/RFID/CMD", "DENY")
            
            # Ajout/Suppression rapide via MQTT (Optionnel)
            elif topic == "RFID/ADD":
                if self.db.creer_badge_rapide(payload): client.publish("parking/RFID/CMD", "ADDED")
            elif topic == "RFID/DEL":
                if self.db.supprimer_par_badge(payload): client.publish("parking/RFID/CMD", "DELETED")

        except Exception as e: print(f"Err MQTT: {e}")

    def publish(self, topic, msg):
        self.client.publish(f"parking/{topic}", msg)

mqtt = MqttHandler(db)

# ==========================================
# 3. VISION & IA (THREADS)
# ==========================================
class CameraThread:
    def __init__(self, src=0):
        self.src = src
        self.frame = None
        self.stopped = False
        self.lock = threading.Lock()
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        cap = cv2.VideoCapture(self.src, cv2.CAP_V4L2)
        # Optimisation Flux
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        while not self.stopped:
            ret, img = cap.read()
            if ret:
                with self.lock: self.frame = img
            else:
                cap.release(); time.sleep(1); cap.open(self.src, cv2.CAP_V4L2)
            time.sleep(0.01)

    def read(self):
        with self.lock: return self.frame.copy() if self.frame is not None else None

cam_in_thread = CameraThread(CAM_ENTRY)
cam_out_thread = CameraThread(CAM_EXIT)

# Configuration OCR
base_dir = os.path.dirname(os.path.abspath(__file__))
xml_path = os.path.join(base_dir, 'haarcascade_russian_plate_number.xml')
plate_cascade = cv2.CascadeClassifier(xml_path)
config_tess = '--psm 7 -c tessedit_char_whitelist=ABCDEFGHJKLMNPQRSTVWXYZ0123456789-'

# États globaux pour l'affichage vidéo
current_view = {"in": None, "out": None}
last_activity = {"in": 0, "out": 0}
vote_buffers = {"in": [], "out": []}
display = {
    "in":  {"plate": "...", "info": "Attente Badge...", "color": (150,150,150), "box": None},
    "out": {"plate": "...", "info": "Pret", "color": (150,150,150), "box": None}
}

def fix_siv(text):
    """Nettoyage OCR pour format AA-123-BB"""
    clean = text.replace('-', '').replace(' ', '')
    if len(clean) != 7: return text
    # Remplacement des confusions classiques (ex: 5 -> S)
    # ... (Garde ta logique de remplacement ici si tu veux, simplifié pour l'exemple)
    return f"{clean[:2]}-{clean[2:5]}-{clean[5:]}"

def process_image_snapshot(img, zone):
    global current_view, last_activity, vote_buffers, last_rfid_unlock
    try:
        # 1. Vérification RFID (Seulement pour l'entrée)
        rfid_valide = True if zone == "out" else (time.time() - last_rfid_unlock) < RFID_TIMEOUT
        
        display[zone]["info"] = "Badgez SVP !" if (zone=="in" and not rfid_valide) else "Scan..."

        # 2. Détection Plaque
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        plates = plate_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 10))
        
        found_roi = None
        if len(plates) > 0:
            (x, y, w, h) = max(plates, key=lambda r: r[2]*r[3])
            display[zone]["box"] = np.array([[x,y], [x+w,y], [x+w,y+h], [x,y+h]], dtype=np.int32)
            found_roi = gray[y:y+h, x:x+w]
            last_activity[zone] = time.time()

        if found_roi is not None:
            if zone == "in" and not rfid_valide:
                display[zone]["color"] = (0, 0, 255); return # Rouge si pas de badge

            # 3. OCR Tesseract
            txt = pytesseract.image_to_string(found_roi, config=config_tess)
            clean_txt = "".join([c for c in txt if c.isalnum() or c=='-'])
            
            # Format simple pour démo, améliore ton regex si besoin
            if len(clean_txt) >= 7: 
                candidate = fix_siv(clean_txt)
                vote_buffers[zone].append(candidate)
                display[zone]["color"] = (0, 255, 255) # Jaune (Analyse)

                # 4. Décision après X lectures
                if len(vote_buffers[zone]) >= SAMPLES_TO_TAKE:
                    most_common = Counter(vote_buffers[zone]).most_common(1)[0][0]
                    vote_buffers[zone] = []
                    
                    if most_common != current_view[zone]:
                        # --- APPEL BASE DE DONNÉES ---
                        if zone == "in":
                            res_db = db.process_entree(most_common)
                            mqtt.publish("barrier_0/state", "OPEN")
                        else:
                            res_db = db.process_sortie(most_common)
                            mqtt.publish("barrier_1/state", "OPEN")
                            threading.Timer(5.0, lambda: mqtt.publish("barrier_1/state", "CLOSE")).start()

                        # --- FEEDBACK ---
                        if lcd: 
                            with lcd_lock: lcd.clear(); lcd.scroll_text(f"{most_common}"); lcd.scroll_text(res_db)
                        
                        display[zone]["plate"] = most_common
                        display[zone]["info"] = res_db
                        display[zone]["color"] = (0, 255, 0) # Vert
                        current_view[zone] = most_common

        # Reset affichage après inactivité
        if time.time() - last_activity[zone] > 5.0:
            vote_buffers[zone] = []
            if current_view[zone]:
                current_view[zone] = None
                display[zone]["plate"] = "..."
                display[zone]["color"] = (150, 150, 150)
                display[zone]["box"] = None

    except Exception as e: pass

def ia_loop():
    while True:
        time.sleep(0.05) # ~20 FPS
        img_in = cam_in_thread.read(); img_out = cam_out_thread.read()
        if img_in is not None: process_image_snapshot(img_in, "in")
        if img_out is not None: process_image_snapshot(img_out, "out")

threading.Thread(target=ia_loop, daemon=True).start()

# ==========================================
# 4. FLASK WEB SERVER
# ==========================================

# --- ROUTES AUTH ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.verifier_login(username, password)
        if user:
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Identifiants incorrects')
    return render_template('login.html') # Assure-toi d'avoir login.html

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- ROUTE DASHBOARD (COMBINÉ) ---
@app.route('/')
@login_required
def index():
    vehicles_data = []
    calendar_data = {}
    
    # Logique spécifique UTILISATEUR
    if current_user.role == 'USER':
        # 1. Cartes Véhicules
        for plaque in current_user.plaques:
            info = db.get_last_entry(plaque)
            if info:
                 raw_date = str(info['entree'])
                 try:
                    dt_entree = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
                    info['date_affichee'] = dt_entree.strftime("le %d-%m-%Y à %H:%M:%S")
                    if info['etat'] == 'GARÉ':
                        delta = datetime.now() - dt_entree
                        minutes = int(delta.total_seconds() / 60)
                        if minutes < 60: info['duree_txt'] = f"{minutes} min"
                        else: info['duree_txt'] = f"{int(minutes/60)}h{minutes%60:02d}"
                    else: info['duree_txt'] = ""
                 except: 
                     info['date_affichee'] = raw_date; info['duree_txt'] = "?"
                 info['numero'] = plaque
                 vehicles_data.append(info)
            else:
                 vehicles_data.append({'numero': plaque, 'etat': 'INCONNU', 'date_affichee': '-', 'duree_txt': ''})

        # 2. Données Calendrier
        raw_history = db.get_full_user_history(current_user.plaques)
        for row in raw_history:
            try:
                dt_in = datetime.strptime(str(row['entree']), "%Y-%m-%d %H:%M:%S")
                date_key = dt_in.strftime("%Y-%m-%d")
                
                if row['sortie']:
                    dt_out = datetime.strptime(str(row['sortie']), "%Y-%m-%d %H:%M:%S")
                    duree = dt_out - dt_in
                    heure_sortie = dt_out.strftime("%H:%M")
                else:
                    duree = datetime.now() - dt_in
                    heure_sortie = "En cours"
                
                hours = int(duree.total_seconds()) // 3600
                duree_str = f"{hours}h { (int(duree.total_seconds())%3600)//60 }min"
                info_html = f"<div><strong>{row['plaque']}</strong><br>Entrée: {dt_in.strftime('%H:%M')}<br>Sortie: {heure_sortie}<br>Temps: {duree_str}</div><hr style='margin:2px 0; border-color:#555'>"
                
                if date_key in calendar_data: calendar_data[date_key] += info_html
                else: calendar_data[date_key] = info_html
            except: pass

    return render_template('dashboard.html', 
                           user=current_user, 
                           vehicles=vehicles_data, 
                           badges=current_user.badges, # Passage des badges
                           calendar_data=json.dumps(calendar_data))

# --- API DONNÉES ---
@app.route('/api/users')
@login_required
def api_users():
    if current_user.role != 'IT': return jsonify([])
    return jsonify(db.get_all_users())

@app.route('/api/json') # Historique
@login_required
def api_history():
    try:
        with db.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM historique ORDER BY id DESC LIMIT 50")
            return jsonify([dict(r) for r in c.fetchall()])
    except: return jsonify([])

@app.route('/api/mqtt_logs')
@login_required
def api_mqtt_logs():
    return jsonify(mqtt_logs)

# --- API ACTIONS (CRUD) ---
@app.route('/api/add_user', methods=['POST'])
@login_required
def api_add_user():
    if current_user.role != 'IT': return jsonify({"success": False})
    data = request.json
    try:
        pwd_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        p_list = [p.strip() for p in data.get('plaque','').split(',') if p.strip()]
        b_list = [b.strip() for b in data.get('badge','').split(',') if b.strip()] # Badges
        
        u = User(nom=data['nom'], role=data['role'], password=pwd_hash, 
                 plaques=p_list, badges=b_list, email=data['email'], tel=data.get('tel',''))
        return jsonify({"success": db.ajouter_user(u)})
    except Exception as e: return jsonify({"success": False, "msg": str(e)})

@app.route('/api/update_user', methods=['POST'])
@login_required
def api_update_user():
    if current_user.role != 'IT': return jsonify({"success": False})
    data = request.json
    p_list = [p.strip() for p in data.get('plaque','').split(',') if p.strip()]
    b_list = [b.strip() for b in data.get('badge','').split(',') if b.strip()]
    
    success = db.update_user_info(data['id'], data['nom'], data['role'], p_list, b_list, data['email'], data.get('tel',''))
    return jsonify({"success": success})

@app.route('/api/delete_user', methods=['POST'])
@login_required
def api_delete_user():
    if current_user.role != 'IT': return jsonify({"success": False})
    return jsonify({"success": db.delete_user_by_id(request.json['id'])})

@app.route('/api/update_profile', methods=['POST'])
@login_required
def api_update_profile():
    data = request.json
    success = db.update_self_profile(current_user.id, data.get('email'), data.get('tel'), data.get('password'))
    return jsonify({"success": success})

# --- API CONTROLE MANUEL (NEW) ---
@app.route('/api/control', methods=['POST'])
@login_required
def api_control():
    if current_user.role != 'IT': return jsonify({"success": False})
    data = request.json
    try:
        if data['type'] == 'barrier':
            topic = f"barrier_{0 if data['gate']=='in' else 1}/state"
            mqtt.publish(topic, data['cmd'])
            print(f"🎮 [MANUEL] {topic} -> {data['cmd']}")
        elif data['type'] == 'lcd':
            if lcd: 
                with lcd_lock: lcd.clear(); lcd.scroll_text(data['text'])
            print(f"🎮 [MANUEL] LCD -> {data['text']}")
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "msg": str(e)})

# --- STREAM VIDEO ---
def gen_frames(zone):
    cam = cam_in_thread if zone == "in" else cam_out_thread
    while True:
        frame = cam.read()
        if frame is None:
            time.sleep(0.1); continue
        
        # Incrustation Infos
        d = display[zone]
        if d["box"] is not None: cv2.polylines(frame, [d["box"]], True, (0, 255, 0), 3)
        # Bandeau noir
        cv2.rectangle(frame, (0,0), (640, 70), (0,0,0), -1)
        cv2.putText(frame, d["plate"], (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, d["color"], 2)
        cv2.putText(frame, d["info"], (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)

        try:
            ret, buf = cv2.imencode('.jpg', frame)
            if ret: yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
        except: break

@app.route('/vid_in')
@login_required
def vid_in(): return Response(gen_frames("in"), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/vid_out')
@login_required
def vid_out(): return Response(gen_frames("out"), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- MAIN ---
if __name__ == '__main__':
    print("🚀 Démarrage Système Parking...")
    # Thread Capteur Température en fond
    def sensor_loop():
        while True:
            if sensor and lcd:
                t = sensor.get_temperature()
                if t: 
                    with lcd_lock: lcd.clear(); lcd.afficher_texte_fixe(f"{t}C")
            time.sleep(10)
    threading.Thread(target=sensor_loop, daemon=True).start()

    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)