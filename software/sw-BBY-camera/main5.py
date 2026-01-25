import cv2
import pytesseract
import threading
import time
import re
import numpy as np
import sqlite3
import os
from datetime import datetime
from collections import Counter
from flask import Flask, Response, jsonify, render_template

# --- IMPORT MODULES MATERIELS ---
from src.lcd_manager import LcdManager
from src.sensor_manager import SensorManager
from src.mqtt_manager import MqttManager

app = Flask(__name__)

# --- CONFIGURATION ---
CAM_ENTRY = 1
CAM_EXIT = 3
DB_PATH = "/home/vcauq/parking.db"
# On garde 3 votes, mais on laisse plus de temps pour les faire
SAMPLES_TO_TAKE = 3  
LCD_CS = 0
SENSOR_CS = 1

# ==========================================
# 1. GESTION BASE DE DONNÉES
# ==========================================
class ParkingDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_tables()

    def connect(self): return sqlite3.connect(self.db_path, timeout=5)

    def init_tables(self):
        try:
            with self.connect() as conn:
                conn.execute('''CREATE TABLE IF NOT EXISTS historique (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plaque TEXT NOT NULL,
                        entree TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        sortie TIMESTAMP,
                        etat TEXT DEFAULT 'GARÉ')''')
                conn.execute('''CREATE TABLE IF NOT EXISTS badges (
                        uid TEXT PRIMARY KEY, nom TEXT, date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                conn.commit()
        except: pass

    def gestion_entree_sortie(self, plaque, zone):
        res = "Erreur"
        try:
            with self.connect() as conn:
                c = conn.cursor()
                now = datetime.now()
                h_actu = now.strftime("%H:%M:%S")
                if zone == "in":
                    c.execute("SELECT id FROM historique WHERE plaque = ? AND etat = 'GARÉ'", (plaque,))
                    if c.fetchone(): res = "Deja la"
                    else:
                        c.execute("INSERT INTO historique (plaque, etat, entree) VALUES (?, 'GARÉ', ?)", (plaque, now))
                        conn.commit()
                        res = f"Entree {h_actu}"
                else:
                    c.execute("SELECT id FROM historique WHERE plaque = ? AND etat = 'GARÉ'", (plaque,))
                    data = c.fetchone()
                    if data:
                        c.execute("UPDATE historique SET sortie = ?, etat = 'PARTI' WHERE id = ?", (now, data[0]))
                        conn.commit()
                        res = f"Sortie {h_actu}"
                    else: res = "Sortie (Inconnu)"
            return res
        except: return "Err SQL"

    def verifier_badge(self, uid):
        try:
            with self.connect() as conn:
                res = conn.execute("SELECT nom FROM badges WHERE uid = ?", (uid,)).fetchone()
                return res[0] if res else None
        except: return None

    def creer_badge_rapide(self, uid):
        try:
            with self.connect() as conn:
                conn.execute("INSERT INTO badges (uid, nom) VALUES (?, ?)", (uid, f"USER_{uid[-4:]}"))
                conn.commit()
            return True
        except: return False

    def supprimer_par_badge(self, uid):
        try:
            with self.connect() as conn:
                c = conn.execute("DELETE FROM badges WHERE uid = ?", (uid,))
                conn.commit()
                return c.rowcount > 0
        except: return False

# --- INIT VARIABLES ---
lcd = None; sensor = None; mqtt = None; db = None 
lcd_lock = threading.Lock()

print("--- INIT MATERIEL ---")
try:
    db = ParkingDatabase(DB_PATH)
    lcd = LcdManager(cs_pin=LCD_CS)
    sensor = SensorManager(cs_pin=SENSOR_CS)
    mqtt = MqttManager(db_manager=db)
    print("✅ OK")
except Exception as e: print(f"⚠️ Erreur: {e}")

# --- CLASSE CAMERA THREADÉE (Capture en continu) ---
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
            time.sleep(0.001) # Max FPS pour le web

    def read(self):
        with self.lock: return self.frame.copy() if self.frame is not None else None

# Lancement Caméras
cam_in_thread = CameraThread(CAM_ENTRY)
cam_out_thread = CameraThread(CAM_EXIT)
time.sleep(2)

# --- XML & CONFIG IA ---
base_dir = os.path.dirname(os.path.abspath(__file__))
xml_file = 'haarcascade_russian_plate_number.xml'
xml_path = os.path.join(base_dir, xml_file)
if not os.path.exists(xml_path): xml_path = os.path.join(os.path.dirname(base_dir), xml_file)
if not os.path.exists(xml_path): xml_path = xml_file 
plate_cascade = cv2.CascadeClassifier(xml_path)

current_view = {"in": None, "out": None}
last_activity = {"in": 0, "out": 0}
vote_buffers = {"in": [], "out": []}
display = {
    "in":  {"plate": "...", "info": "Pret", "color": (150,150,150), "box": None},
    "out": {"plate": "...", "info": "Pret", "color": (150,150,150), "box": None}
}
config_tess = '--psm 7 -c tessedit_char_whitelist=ABCDEFGHJKLMNPQRSTVWXYZ0123456789-'

# --- FONCTIONS VISION ---
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
    """Traitement 'Snapshot' allégé"""
    global current_view, last_activity, vote_buffers
    try:
        # 1. CROP : On ne garde que les 60% du bas (On enlève le ciel)
        h, w = img.shape[:2]
        crop_img = img[int(h*0.4):h, 0:w] # On coupe 40% du haut
        
        gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
        
        # 2. DETECTION RAPIDE
        plates = plate_cascade.detectMultiScale(gray, 1.1, 4, minSize=(60, 20))
        
        found_roi = None
        display_box = None
        
        if len(plates) > 0:
            # On remet les coordonnées à l'échelle de l'image complète
            (x, y_crop, wb, hb) = max(plates, key=lambda r: r[2]*r[3])
            y = y_crop + int(h*0.4) # On rajoute le décalage du crop
            
            display_box = np.array([[x,y], [x+wb,y], [x+wb,y+hb], [x,y+hb]], dtype=np.int32)
            
            # Extraction ROI
            roi = gray[y_crop:y_crop+hb, x:x+wb] # On travaille sur le crop gris
            found_roi = roi

        if found_roi is not None:
            last_activity[zone] = time.time()
            display[zone]["box"] = display_box
            
            # Lecture Tesseract
            final_img = enhance_plate(cv2.resize(found_roi, (300, 75)))
            txt = pytesseract.image_to_string(final_img, config=config_tess)
            cln = "".join([x for x in txt if x.isalnum()])
            corr = fix_siv(cln)
            
            if re.search(r"([A-Z]{2})-?([0-9]{3})-?([A-Z]{2})", corr):
                # On formate proprement
                clean_match = re.search(r"([A-Z]{2})-?([0-9]{3})-?([A-Z]{2})", corr)
                candidate = f"{clean_match.group(1)}-{clean_match.group(2)}-{clean_match.group(3)}"
                
                vote_buffers[zone].append(candidate)
                
                if len(vote_buffers[zone]) < SAMPLES_TO_TAKE:
                    display[zone]["info"] = f"Scan {len(vote_buffers[zone])}/{SAMPLES_TO_TAKE}"
                    display[zone]["color"] = (0, 255, 255)
                else:
                    # VICTOIRE
                    most_common = Counter(vote_buffers[zone]).most_common(1)[0][0]
                    vote_buffers[zone] = []
                    
                    if most_common != current_view[zone]:
                        info_db = db.gestion_entree_sortie(most_common, zone)
                        if mqtt: mqtt.publish("entree" if zone=="in" else "sortie", f"{most_common}|{info_db}")
                        
                        # LCD Thread
                        threading.Thread(target=animation_lcd, args=(most_common, zone)).start()
                        
                        display[zone]["plate"] = most_common
                        display[zone]["info"] = info_db
                        display[zone]["color"] = (0, 255, 0)
                        print(f"[{zone}] WINNER: {most_common}")
                        current_view[zone] = most_common

        # Timeout augmenté à 10s car on analyse moins souvent
        if time.time() - last_activity[zone] > 10.0:
            vote_buffers[zone] = []
            if current_view[zone]:
                current_view[zone] = None
                display[zone]["plate"] = "..."; display[zone]["info"] = "Pret"; display[zone]["color"] = (150, 150, 150); display[zone]["box"] = None

    except Exception as e: pass

def animation_lcd(plaque, zone):
    if lcd:
        with lcd_lock:
            lcd.clear(); lcd.scroll_text(f"{plaque}"); time.sleep(0.5)
            if zone=="out": lcd.scroll_text("AU REVOIR"); time.sleep(0.5)
            lcd.clear()

# --- THREAD INTELLIGENCE ARTIFICIELLE (Frame Skip) ---
def ia_loop():
    frame_counter = 0
    while True:
        # On dort un peu (boucle de base)
        time.sleep(0.05) 
        frame_counter += 1
        
        # ON ANALYSE SEULEMENT 1 FOIS TOUTES LES 10 FRAMES (environ toutes les 0.5s)
        # C'est CA qui va décharger ton CPU et rendre le tout fluide
        if frame_counter % 10 != 0:
            continue
            
        img_in = cam_in_thread.read()
        img_out = cam_out_thread.read()
        
        if img_in is not None: process_image_snapshot(img_in, "in")
        if img_out is not None: process_image_snapshot(img_out, "out")

threading.Thread(target=ia_loop, daemon=True).start()

# --- THREAD LCD ---
def boucle_physique():
    while True:
        try:
            if lcd:
                with lcd_lock: lcd.clear(); lcd.scroll_text("   BIENVENUE   ")
            time.sleep(1)
            if lcd:
                with lcd_lock: lcd.clear(); lcd.afficher_texte_fixe(datetime.now().strftime("%H:%M"))
            time.sleep(3) 
            if sensor and lcd:
                t = sensor.get_temperature()
                if t: 
                    with lcd_lock: lcd.clear(); lcd.afficher_texte_fixe(f"{t}C")
                time.sleep(3)
            time.sleep(0.5)
        except: time.sleep(5)
threading.Thread(target=boucle_physique, daemon=True).start()

# --- WEB ---
def gen(zone):
    cam = cam_in_thread if zone == "in" else cam_out_thread
    while True:
        frame_copy = cam.read()
        if frame_copy is None:
            frame_copy = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame_copy, "CHARGEMENT...", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
            time.sleep(0.5)
        else:
            d = display[zone]
            if d["box"] is not None: cv2.polylines(frame_copy, [d["box"]], True, (0, 255, 0), 3)
            cv2.rectangle(frame_copy, (0,0), (640, 70), (0,0,0), -1)
            cv2.putText(frame_copy, d["plate"], (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, d["color"], 2)
            cv2.putText(frame_copy, d["info"], (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
        
        try:
            ret, buf = cv2.imencode('.jpg', frame_copy)
            if ret: yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
        except: pass

@app.route('/')
def index(): return render_template('index.html')

@app.route('/vid_in')
def vid_in(): return Response(gen("in"), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/vid_out')
def vid_out(): return Response(gen("out"), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/json')
def get_json():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM historique ORDER BY id DESC LIMIT 100")
            return jsonify([dict(r) for r in c.fetchall()])
    except: return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
