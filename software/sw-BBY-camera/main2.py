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
from flask import Flask, Response, jsonify

# --- IMPORT MODULES MATERIELS ---
from src.lcd_manager import LcdManager
from src.sensor_manager import SensorManager
from src.mqtt_manager import MqttManager

app = Flask(__name__)

# --- CONFIGURATION ---
CAM_ENTRY = 1
CAM_EXIT = 3
DB_PATH = "/home/vcauq/parking.db"
SAMPLES_TO_TAKE = 3
LCD_CS = 0
SENSOR_CS = 1

# --- INIT MATERIEL ---
print("--- INIT MATERIEL ---")
try:
    lcd = LcdManager(cs_pin=LCD_CS)
    sensor = SensorManager(cs_pin=SENSOR_CS)
    mqtt = MqttManager()
    print("✅ LCD / SENSOR / MQTT : OK")
except Exception as e:
    print(f"⚠️ Erreur Matériel : {e}")
    lcd = None; sensor = None; mqtt = None

lcd_lock = threading.Lock()

# --- CHARGEMENT XML ---
base_dir = os.path.dirname(os.path.abspath(__file__))
xml_file = 'haarcascade_russian_plate_number.xml'
xml_path = os.path.join(base_dir, xml_file)
if not os.path.exists(xml_path):
    xml_path = os.path.join(os.path.dirname(base_dir), xml_file)
if not os.path.exists(xml_path):
    xml_path = xml_file 

print(f"Chargement XML : {xml_path}")
plate_cascade = cv2.CascadeClassifier(xml_path)

# --- VARIABLES ---
frames = {"in": None, "out": None}
locks = {"in": threading.Lock(), "out": threading.Lock()}
current_view = {"in": None, "out": None}
last_activity = {"in": 0, "out": 0}
vote_buffers = {"in": [], "out": []}

display = {
    "in":  {"plate": "...", "info": "Pret", "color": (150,150,150), "box": None},
    "out": {"plate": "...", "info": "Pret", "color": (150,150,150), "box": None}
}

allowed = "ABCDEFGHJKLMNPQRSTVWXYZ0123456789-"
config_tess = f'--psm 7 -c tessedit_char_whitelist={allowed}'

# --- INIT DB ---
def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS historique (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plaque TEXT NOT NULL,
                    entree TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sortie TIMESTAMP,
                    etat TEXT DEFAULT 'GARÉ')''')
            conn.commit()
    except: pass
init_db()

# --- CAMERAS ---
def open_camera(index):
    cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 15)
    return cap

print("Ouverture Caméras...")
cam_entry = open_camera(CAM_ENTRY)
time.sleep(1)
cam_exit = open_camera(CAM_EXIT)

# --- GESTION DB ---
def manage_db(plaque, zone):
    try:
        with sqlite3.connect(DB_PATH, timeout=5) as conn:
            c = conn.cursor()
            now = datetime.now()
            h_actu = now.strftime("%H:%M:%S")
            res = ""
            
            if zone == "in":
                # On vérifie si la voiture est marquée comme "GARÉ"
                c.execute("SELECT id, entree FROM historique WHERE plaque = ? AND etat = 'GARÉ'", (plaque,))
                data = c.fetchone()
                if data:
                    res = "Deja la"
                else:
                    c.execute("INSERT INTO historique (plaque, etat, entree) VALUES (?, 'GARÉ', ?)", (plaque, now))
                    conn.commit()
                    res = f"Entree {h_actu}"
            else:
                # Sortie
                c.execute("SELECT id, entree FROM historique WHERE plaque = ? AND etat = 'GARÉ'", (plaque,))
                data = c.fetchone()
                if data:
                    c.execute("UPDATE historique SET sortie = ?, etat = 'PARTI' WHERE id = ?", (now, data[0]))
                    conn.commit()
                    res = f"Sortie {h_actu}"
                else:
                    res = "Sortie (Inconnu)"
            
            if mqtt:
                topic = "entree" if zone == "in" else "sortie"
                mqtt.publish(topic, f"{plaque}|{res}")
                
            return res
    except Exception as e:
        return "Err SQL"

# --- SCENARIO LCD (CORRIGÉ) ---
def animation_lcd_detection(plaque, zone):
    if lcd is None: return
    with lcd_lock:
        try:
            lcd.clear()
            
            # 1. UNIQUEMENT LE NUMERO (Plus de "PLAQUE:")
            lcd.scroll_text(f"{plaque}")
            time.sleep(0.5)

            # 2. Si c'est la SORTIE, on ajoute "AU REVOIR"
            if zone == "out":
                lcd.scroll_text("AU REVOIR")
                time.sleep(0.5)
            
            lcd.clear()
        except: pass

# --- VISION ---
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
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(img)
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary

def refine_plate_area(roi_gray):
    blur = cv2.GaussianBlur(roi_gray, (5,5), 0)
    edges = cv2.Canny(blur, 50, 200)
    cnts, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02*peri, True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(c)
            ratio = w / float(h)
            if 2 < ratio < 6 and w > 50:
                return roi_gray[y:y+h, x:x+w]
    h, w = roi_gray.shape
    return roi_gray[int(h*0.1):int(h*0.9), int(w*0.05):int(w*0.95)]

# --- ANALYSEUR ---
def process_image(img, zone):
    global current_view, last_activity, vote_buffers
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        plates = plate_cascade.detectMultiScale(gray, 1.1, 4, minSize=(60, 20))
        found_roi = None
        display_box = None
        
        if len(plates) > 0:
            (x,y,w,h) = max(plates, key=lambda r: r[2]*r[3])
            display_box = np.array([[x,y], [x+w,y], [x+w,y+h], [x,y+h]], dtype=np.int32)
            roi_gray = gray[y:y+h, x:x+w]
            found_roi = refine_plate_area(roi_gray)

        if found_roi is not None:
            last_activity[zone] = time.time()
            display[zone]["box"] = display_box
            
            plate_zoom = cv2.resize(found_roi, (300, 75), interpolation=cv2.INTER_CUBIC)
            final_img = enhance_plate(plate_zoom)
            
            txt = pytesseract.image_to_string(final_img, config=config_tess)
            cln = "".join([x for x in txt if x.isalnum()])
            corr = fix_siv(cln)
            match = re.search(r"([A-Z]{2})-?([0-9]{3})-?([A-Z]{2})", corr)
            
            if match:
                candidate = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                vote_buffers[zone].append(candidate)
                
                count = len(vote_buffers[zone])
                if count < SAMPLES_TO_TAKE:
                    display[zone]["info"] = f"Analyse {count}/{SAMPLES_TO_TAKE}"
                    display[zone]["color"] = (0, 255, 255) # Jaune
                
                if count >= SAMPLES_TO_TAKE:
                    most_common, _ = Counter(vote_buffers[zone]).most_common(1)[0]
                    vote_buffers[zone] = []
                    plaque_validated = most_common
                    
                    if plaque_validated != current_view[zone]:
                        info_db = manage_db(plaque_validated, zone)
                        threading.Thread(target=animation_lcd_detection, args=(plaque_validated, zone)).start()

                        display[zone]["plate"] = plaque_validated
                        display[zone]["info"] = info_db
                        display[zone]["color"] = (0, 255, 0) # Vert
                        print(f"[{zone}] WINNER: {plaque_validated}")
                        current_view[zone] = plaque_validated

        if time.time() - last_activity[zone] > 2.0:
            if len(vote_buffers[zone]) > 0: vote_buffers[zone] = []
            if current_view[zone] is not None:
                current_view[zone] = None
                display[zone]["plate"] = "..."
                display[zone]["info"] = "Pret"
                display[zone]["color"] = (150, 150, 150)
                display[zone]["box"] = None

    except Exception as e: pass

def ia_loop():
    while True:
        with locks["in"]:
            im1 = frames["in"].copy() if frames["in"] is not None else None
        if im1 is not None: process_image(im1, "in")
        with locks["out"]:
            im2 = frames["out"].copy() if frames["out"] is not None else None
        if im2 is not None: process_image(im2, "out")
        time.sleep(0.05)

threading.Thread(target=ia_loop, daemon=True).start()

# --- BOUCLE PHYSIQUE ---
def boucle_physique():
    print("[SYSTEM] Démarrage boucle LCD...")
    while True:
        try:
            if lcd:
                with lcd_lock:
                    lcd.clear()
                    lcd.scroll_text("   BIENVENUE   ")
            time.sleep(1)

            if lcd:
                with lcd_lock:
                    lcd.clear()
                    now = datetime.now()
                    lcd.afficher_texte_fixe(now.strftime("%H:%M"))
            time.sleep(3) 
            
            if sensor and lcd:
                temp = sensor.get_temperature()
                if temp is not None:
                    with lcd_lock:
                        lcd.clear()
                        lcd.afficher_texte_fixe(f"{temp}C")
                time.sleep(3)
            time.sleep(0.5)
        except Exception:
            time.sleep(5)

threading.Thread(target=boucle_physique, daemon=True).start()

def gen(zone):
    idx = CAM_ENTRY if zone=="in" else CAM_EXIT
    cap = cam_entry if zone=="in" else cam_exit
    while True:
        s, f = cap.read()
        if not s:
            time.sleep(0.5); 
            try: cap.open(idx, cv2.CAP_V4L2)
            except: pass
            continue
        with locks[zone]: frames[zone] = f.copy()
        d = display[zone]
        if d["box"] is not None:
            cv2.polylines(f, [d["box"]], True, (0, 255, 0), 3)
        cv2.rectangle(f, (0,0), (640, 70), (0,0,0), -1)
        cv2.putText(f, d["plate"], (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, d["color"], 2)
        cv2.putText(f, d["info"], (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
        ret, buf = cv2.imencode('.jpg', f)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')

# --- WEB AVEC HISTORIQUE SCROLLABLE ---
@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html lang="fr" data-bs-theme="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial_scale=1.0">
        <title>Parking Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
        <style>
            body { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
            .card-video { background-color: #1e1e1e; border: 1px solid #333; border-radius: 10px; overflow: hidden; margin-bottom: 20px; }
            .card-header { font-weight: bold; text-align: center; padding: 10px; color: white; text-transform: uppercase; }
            .header-in { background-color: #198754; } 
            .header-out { background-color: #dc3545; }
            .video-stream { width: 100%; height: auto; display: block; border-bottom: 1px solid #333; }
            
            /* SCROLLBAR POUR HISTORIQUE */
            .history-scroll-area {
                max-height: 350px;
                overflow-y: auto;
                border: 1px solid #333;
                border-radius: 5px;
            }
            /* Custom Scrollbar */
            .history-scroll-area::-webkit-scrollbar { width: 8px; }
            .history-scroll-area::-webkit-scrollbar-track { background: #1e1e1e; }
            .history-scroll-area::-webkit-scrollbar-thumb { background: #444; border-radius: 4px; }
            
            .table-container { background-color: #1e1e1e; border-radius: 10px; padding: 20px; border: 1px solid #333; margin-bottom: 50px; }
            .badge-gar { background-color: #28a745; color: white; }
            .badge-parti { background-color: #6c757d; color: white; }
        </style>
    </head>
    <body>
        <div class="container py-4">
            <h1 class="text-center mb-4 display-6 fw-bold">🅿️ Parking Control Center</h1>

            <div class="row g-4">
                <div class="col-lg-6">
                    <div class="card-video">
                        <div class="card-header header-in"><i class="bi bi-box-arrow-in-right"></i> Entrée</div>
                        <img src="/vid_in" class="video-stream">
                    </div>
                </div>
                <div class="col-lg-6">
                    <div class="card-video">
                        <div class="card-header header-out"><i class="bi bi-box-arrow-left"></i> Sortie</div>
                        <img src="/vid_out" class="video-stream">
                    </div>
                </div>
            </div>

            <div class="row mt-4">
                <div class="col-12">
                    <div class="table-container">
                        <h4 class="mb-3"><i class="bi bi-clock-history"></i> Historique (Scrollable)</h4>
                        
                        <div class="history-scroll-area">
                            <table class="table table-dark table-striped table-hover align-middle mb-0">
                                <thead style="position: sticky; top: 0; background-color: #2c2c2c; z-index: 1;">
                                    <tr>
                                        <th>Plaque</th>
                                        <th>Entrée</th>
                                        <th>Sortie</th>
                                        <th>État</th>
                                    </tr>
                                </thead>
                                <tbody id="history-body"></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            function updateHistory() {
                fetch('/api/json')
                    .then(response => response.json())
                    .then(data => {
                        const tbody = document.getElementById('history-body');
                        if (!data) return;

                        let html = '';
                        data.forEach((row) => {
                            // LOGIQUE D'AFFICHAGE ETAT : On affiche "ENTRÉ" même si la DB dit "GARÉ"
                            let etatAffiche = "PARTI";
                            let badgeClass = "badge-parti";

                            if (row.etat === 'GARÉ' || row.etat === 'ENTRÉ') {
                                etatAffiche = "ENTRÉ"; // Demande utilisateur
                                badgeClass = "badge-gar";
                            }
                            
                            let entreeStr = row.entree ? row.entree.split(' ')[1] : '?';
                            let sortieStr = row.sortie ? row.sortie.split(' ')[1] : '-';

                            html += `
                                <tr>
                                    <td><span class="fw-bold text-white" style="letter-spacing:1px">${row.plaque}</span></td>
                                    <td>${entreeStr}</td>
                                    <td>${sortieStr}</td>
                                    <td><span class="badge ${badgeClass}">${etatAffiche}</span></td>
                                </tr>`;
                        });
                        
                        // Optimisation: ne met à jour que si ça a changé
                        if(tbody.innerHTML !== html) {
                            tbody.innerHTML = html;
                        }
                    })
                    .catch(err => console.log(err));
            }

            setInterval(updateHistory, 2000);
            updateHistory();
        </script>
    </body>
    </html>
    """

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
            # On charge 100 lignes pour que le scroll soit utile
            c.execute("SELECT * FROM historique ORDER BY id DESC LIMIT 100")
            return jsonify([dict(r) for r in c.fetchall()])
    except: return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)