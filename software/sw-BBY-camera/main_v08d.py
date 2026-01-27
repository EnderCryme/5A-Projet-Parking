import cv2
import pytesseract
import threading
import time
import re
import numpy as np
import os
import json
import hashlib
from datetime import datetime
from collections import Counter
from flask import Flask, Response, jsonify, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

# --- IMPORT MODULES CUSTOM ---
from src.db_manager import DbManager, User
from src.lcd_manager import LcdManager
from src.sensor_manager import SensorManager
from src.mqtt_manager import MqttManager 

# --- CONFIGURATION ---
CAM_ENTRY = 3
CAM_EXIT = 1
DB_PATH = "/home/vcauq/sw-BBY-camera/parking.db"
SAMPLES_TO_TAKE = 3 
LCD_CS = 0
SENSOR_CS = 1

app = Flask(__name__)
app.secret_key = 'SECRET_KEY_PROD'

# --- VARIABLES GLOBALES ---
lcd = None
sensor = None
db = None 
mqtt = None
lcd_lock = threading.Lock()
mqtt_logs = [] 

# ==========================================
# 1. INITIALISATION
# ==========================================

# DB & LOGIN
db = DbManager(DB_PATH)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.get_user_by_id(user_id)

# MQTT
mqtt = MqttManager(db_manager=db, logs_list=mqtt_logs)

# MATÉRIEL
print("--- INIT MATERIEL ---")
try:
    lcd = LcdManager(cs_pin=LCD_CS)
    sensor = SensorManager(cs_pin=SENSOR_CS)
    print("✅ LCD & Capteurs OK")
except Exception as e: 
    print(f"⚠️ Mode Simulation (Pas de GPIO): {e}")

# ==========================================
# 2. VISION & IA
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
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        while not self.stopped:
            ret, img = cap.read()
            if ret:
                with self.lock: self.frame = img
            else:
                cap.release(); time.sleep(1); cap.open(self.src, cv2.CAP_V4L2)
            time.sleep(0.005)

    def read(self):
        with self.lock: return self.frame.copy() if self.frame is not None else None

cam_in_thread = CameraThread(CAM_ENTRY)
cam_out_thread = CameraThread(CAM_EXIT)
time.sleep(2)

# Config OCR
base_dir = os.path.dirname(os.path.abspath(__file__))
xml_path = os.path.join(base_dir, 'haarcascade_russian_plate_number.xml')
plate_cascade = cv2.CascadeClassifier(xml_path)
config_tess = '--psm 7 -c tessedit_char_whitelist=ABCDEFGHJKLMNPQRSTVWXYZ0123456789-'

# États Affichage
current_view = {"in": None, "out": None}
last_activity = {"in": 0, "out": 0}
vote_buffers = {"in": [], "out": []}
display = {
    "in":  {"plate": "...", "info": "Attente Badge...", "color": (150,150,150), "box": None},
    "out": {"plate": "...", "info": "Pret", "color": (150,150,150), "box": None}
}

# --- FONCTION DE NETTOYAGE ---
def fix_siv(text):
    clean = text.replace('-', '').replace(' ', '')
    if len(clean) != 7: return text
    l = list(clean)
    to_let = {'8':'B','5':'S','2':'Z','4':'A','6':'G','0':'D'}
    to_num = {'B':'8','S':'5','Z':'2','A':'4','G':'6','Q':'0','D':'0'}
    for i in [0,1,5,6]: 
        if l[i].isdigit() and l[i] in to_let: l[i] = to_let[l[i]]
    for i in [2,3,4]:
        if l[i].isalpha() and l[i] in to_num: l[i] = to_num[l[i]]
    return f"{l[0]}{l[1]}-{l[2]}{l[3]}{l[4]}-{l[5]}{l[6]}"

def enhance_plate(img):
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape)==3 else img
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        return cv2.threshold(clahe.apply(gray), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    except: return img

def process_image_snapshot(img, zone):
    global current_view, last_activity, vote_buffers
    try:
        # 1. Vérification RFID
        rfid_valide = True if zone == "out" else mqtt.is_unlock_active()
        display[zone]["info"] = "Badgez SVP !" if (zone=="in" and not rfid_valide) else "Scan..."

        # 2. Détection / Crop
        h, w = img.shape[:2]
        crop_img = img[int(h*0.4):h, 0:w]
        gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
        small_gray = cv2.resize(gray, (0,0), fx=0.5, fy=0.5)
        plates = plate_cascade.detectMultiScale(small_gray, 1.1, 4, minSize=(30, 10))
        
        found_roi = None
        if len(plates) > 0:
            (xs, ys, ws, hs) = max(plates, key=lambda r: r[2]*r[3])
            x, y_crop, wb, hb = xs*2, ys*2, ws*2, hs*2
            y = y_crop + int(h*0.4)
            display[zone]["box"] = np.array([[x,y], [x+wb,y], [x+wb,y+hb], [x,y+hb]], dtype=np.int32)
            found_roi = gray[y_crop:y_crop+hb, x:x+wb]
            last_activity[zone] = time.time()

        if found_roi is not None:
            if zone == "in" and not rfid_valide:
                display[zone]["color"] = (0, 0, 255); return 

            # 3. OCR & Regex
            final_img = enhance_plate(cv2.resize(found_roi, (300, 75)))
            txt = pytesseract.image_to_string(final_img, config=config_tess)
            cln = "".join([c for c in txt if c.isalnum()])
            corr = fix_siv(cln)

            # --- CORRECTION DE L'ERREUR D'INDENTATION ICI ---
            match = re.search(r"([A-Z]{2})-?([0-9]{3})-?([A-Z]{2})", corr)
            
            if match:
                candidate = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                vote_buffers[zone].append(candidate)
                display[zone]["color"] = (0, 255, 255) # Jaune

                # MISE A JOUR TEMPS REEL (HUD)
                display[zone]["plate"] = candidate
                display[zone]["info"] = f"Analyse {len(vote_buffers[zone])}/{SAMPLES_TO_TAKE}..."

                # 4. Décision
                if len(vote_buffers[zone]) >= SAMPLES_TO_TAKE:
                    most_common = Counter(vote_buffers[zone]).most_common(1)[0][0]
                    vote_buffers[zone] = []
                    
                    if most_common != current_view[zone]:
                        if zone == "in":
                            res_db = db.process_entree(most_common)
                            mqtt.publish("barrier_0/state", "OPEN")
                        else:
                            res_db = db.process_sortie(most_common)
                            mqtt.publish("barrier_1/state", "OPEN")
                            threading.Timer(5.0, lambda: mqtt.publish("barrier_1/state", "CLOSE")).start()

                        if lcd: 
                            with lcd_lock: lcd.clear(); lcd.scroll_text(f"{most_common}"); lcd.scroll_text(res_db)
                        
                        display[zone]["plate"] = most_common
                        display[zone]["info"] = res_db
                        display[zone]["color"] = (0, 255, 0)
                        current_view[zone] = most_common

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
        time.sleep(0.05)
        img_in = cam_in_thread.read(); img_out = cam_out_thread.read()
        if img_in is not None: process_image_snapshot(img_in, "in")
        if img_out is not None: process_image_snapshot(img_out, "out")

threading.Thread(target=ia_loop, daemon=True).start()

# ==========================================
# 3. WEB SERVER
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.verifier_login(username, password)
        if user: login_user(user); return redirect(url_for('index'))
        else: flash('Identifiants incorrects')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    vehicles_data = []
    calendar_data = {}
    
    if current_user.role == 'USER':
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
                 except: info['date_affichee'] = raw_date; info['duree_txt'] = "?"
                 info['numero'] = plaque
                 vehicles_data.append(info)
            else:
                 vehicles_data.append({'numero': plaque, 'etat': 'INCONNU', 'date_affichee': '-', 'duree_txt': ''})

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
                           badges=current_user.badges,
                           calendar_data=json.dumps(calendar_data))

# --- API ---
@app.route('/api/users')
@login_required
def api_users(): return jsonify(db.get_all_users() if current_user.role == 'IT' else [])

@app.route('/api/json')
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
def api_mqtt_logs(): return jsonify(mqtt_logs)

@app.route('/api/delete_history', methods=['POST'])
@login_required
def api_delete_history():
    if current_user.role != 'IT': return jsonify({"success": False})
    try:
        row_id = request.json['id']
        with db.connect() as conn:
            conn.execute("DELETE FROM historique WHERE id = ?", (row_id,))
            conn.commit()
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "msg": str(e)})

@app.route('/api/add_user', methods=['POST'])
@login_required
def api_add_user():
    if current_user.role != 'IT': return jsonify({"success": False})
    d = request.json
    try:
        ph = hashlib.sha256(d['password'].encode()).hexdigest()
        pl = [p.strip() for p in d.get('plaque','').split(',') if p.strip()]
        bl = [b.strip() for b in d.get('badge','').split(',') if b.strip()]
        u = User(nom=d['nom'], role=d['role'], password=ph, plaques=pl, badges=bl, email=d['email'], tel=d.get('tel',''))
        return jsonify({"success": db.ajouter_user(u)})
    except Exception as e: return jsonify({"success": False, "msg": str(e)})

@app.route('/api/update_user', methods=['POST'])
@login_required
def api_update_user():
    if current_user.role != 'IT': return jsonify({"success": False})
    d = request.json
    pl = [p.strip() for p in d.get('plaque','').split(',') if p.strip()]
    bl = [b.strip() for b in d.get('badge','').split(',') if b.strip()]
    return jsonify({"success": db.update_user_info(d['id'], d['nom'], d['role'], pl, bl, d['email'], d.get('tel',''))})

@app.route('/api/delete_user', methods=['POST'])
@login_required
def api_delete_user():
    if current_user.role != 'IT': return jsonify({"success": False})
    return jsonify({"success": db.delete_user_by_id(request.json['id'])})

@app.route('/api/update_profile', methods=['POST'])
@login_required
def api_update_profile():
    d = request.json
    return jsonify({"success": db.update_self_profile(current_user.id, d.get('email'), d.get('tel'), d.get('password'))})

@app.route('/api/control', methods=['POST'])
@login_required
def api_control():
    if current_user.role != 'IT': return jsonify({"success": False})
    d = request.json
    try:
        if d['type'] == 'barrier':
            topic = f"barrier_{0 if d['gate']=='in' else 1}/state"
            mqtt.publish(topic, d['cmd']) 
        elif d['type'] == 'lcd':
            if lcd: 
                with lcd_lock: lcd.clear(); lcd.scroll_text(d['text'])
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "msg": str(e)})

# --- STREAM VIDEO ---
def gen_frames(zone):
    cam = cam_in_thread if zone == "in" else cam_out_thread
    while True:
        frame = cam.read()
        if frame is None:
            time.sleep(0.1); continue
        
        d = display[zone]
        if d["box"] is not None: cv2.polylines(frame, [d["box"]], True, (0, 255, 0), 3)
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

if __name__ == '__main__':
    print("🚀 Démarrage Système Parking...")
    def sensor_loop():
        while True:
            if sensor and lcd:
                t = sensor.get_temperature()
                if t: 
                    with lcd_lock: lcd.clear(); lcd.afficher_texte_fixe(f"{t}C")
            time.sleep(10)
    threading.Thread(target=sensor_loop, daemon=True).start()

    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
