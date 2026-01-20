import cv2
import threading
import time
import re
import numpy as np
import pytesseract
import os
from collections import Counter

# ==========================================
# 1. FONCTIONS VISION
# ==========================================
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
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(img)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    except: return img

def refine_plate_area(roi_gray):
    try:
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
    except: return roi_gray

# ==========================================
# 2. CLASSE CAMERA MANAGER (OPTIMISÉE)
# ==========================================
class CameraManager:
    def __init__(self, camera_id, role, callback_detection=None):
        self.id = camera_id
        self.role = role
        self.callback = callback_detection
        
        allowed = "ABCDEFGHJKLMNPQRSTVWXYZ0123456789-"
        self.config_tess = f'--psm 7 -c tessedit_char_whitelist={allowed}'
        
        # Chargement XML
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(current_dir)
        xml_filename = 'haarcascade_russian_plate_number.xml'
        self.xml_path = os.path.join(project_dir, xml_filename)
        if not os.path.exists(self.xml_path):
            self.xml_path = f"/home/vcauq/Beagle_project/{xml_filename}"
        if not os.path.exists(self.xml_path):
            self.xml_path = xml_filename

        if os.path.exists(self.xml_path):
            print(f"[CAM {role}] XML OK")
            self.plate_cascade = cv2.CascadeClassifier(self.xml_path)
        else:
            print(f"[CAM {role}] ❌ XML KO")
            self.plate_cascade = None

        self.cap = None
        self.running = False
        self.lock = threading.Lock()
        self.current_frame = None
        
        self.vote_buffer = []
        self.SAMPLES_TO_TAKE = 3
        self.last_valid_plate = None
        self.last_activity = 0
        
        self.display = {"plate": "...", "info": "Pret", "color": (150,150,150), "box": None}

    def start(self):
        print(f"[CAM {self.role}] Start USB {self.id}")
        self.cap = cv2.VideoCapture(self.id, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 15)

        self.running = True
        threading.Thread(target=self._capture_loop, daemon=True).start()
        threading.Thread(target=self._ia_loop, daemon=True).start()

    def stop(self):
        self.running = False
        if self.cap: self.cap.release()

    def _capture_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.5)
                try: self.cap.open(self.id, cv2.CAP_V4L2)
                except: pass
                continue
            with self.lock:
                self.current_frame = frame
            time.sleep(0.02) # Petite pause vitale pour l'écran

    def _ia_loop(self):
        while self.running:
            img = None
            with self.lock:
                if self.current_frame is not None:
                    img = self.current_frame.copy()
            
            if img is not None and self.plate_cascade is not None:
                self._process_image(img)
            
            # On laisse le temps au CPU de respirer
            time.sleep(0.1) 

    def _process_image(self, img):
        try:
            # --- ASTUCE TURBO : DOWNSCALE ---
            # On réduit l'image par 2 pour la détection (beaucoup plus rapide)
            small_frame = cv2.resize(img, (0, 0), fx=0.5, fy=0.5)
            gray_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            
            # On cherche sur la petite image
            plates = self.plate_cascade.detectMultiScale(gray_small, 1.1, 4, minSize=(30, 10))
            
            found_roi = None
            display_box = None
            
            if len(plates) > 0:
                self.last_activity = time.time()
                
                # On prend la plus grande détection sur la petite image
                (xs, ys, ws, hs) = max(plates, key=lambda r: r[2]*r[3])
                
                # On remet à l'échelle (x2) pour l'image HD
                x, y, w, h = xs*2, ys*2, ws*2, hs*2
                display_box = np.array([[x,y], [x+w,y], [x+w,y+h], [x,y+h]], dtype=np.int32)
                
                # On découpe sur l'image ORIGINALE HD pour la lecture Tesseract
                gray_hd = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                roi_gray = gray_hd[y:y+h, x:x+w]
                found_roi = refine_plate_area(roi_gray)

            if found_roi is not None:
                self.display["box"] = display_box
                
                plate_zoom = cv2.resize(found_roi, (300, 75), interpolation=cv2.INTER_CUBIC)
                final_img = enhance_plate(plate_zoom)
                
                txt = pytesseract.image_to_string(final_img, config=self.config_tess)
                cln = "".join([x for x in txt if x.isalnum()])
                corr = fix_siv(cln)
                match = re.search(r"([A-Z]{2})-?([0-9]{3})-?([A-Z]{2})", corr)
                
                if match:
                    candidate = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                    self.vote_buffer.append(candidate)
                    
                    count = len(self.vote_buffer)
                    if count < self.SAMPLES_TO_TAKE:
                        self.display["info"] = f"Scan {count}/{self.SAMPLES_TO_TAKE}..."
                        self.display["color"] = (0, 255, 255) # Jaune
                    
                    elif count >= self.SAMPLES_TO_TAKE:
                        most_common, _ = Counter(self.vote_buffer).most_common(1)[0]
                        self.vote_buffer = [] 
                        
                        if most_common != self.last_valid_plate:
                            self.last_valid_plate = most_common
                            self.display["plate"] = most_common
                            self.display["color"] = (0, 255, 0) # Vert
                            self.display["info"] = "VALIDE"
                            print(f"[CAM {self.role}] WINNER : {most_common}")
                            if self.callback: self.callback(most_common, self.role)

            if time.time() - self.last_activity > 5.0:
                if len(self.vote_buffer) > 0: self.vote_buffer = []
                self.display["plate"] = "..."
                self.display["info"] = "Pret"
                self.display["color"] = (150, 150, 150)
                self.display["box"] = None
                self.last_valid_plate = None

        except Exception as e: pass

    def generate_jpeg(self):
        while True:
            frame_copy = None
            with self.lock:
                if self.current_frame is not None:
                    frame_copy = self.current_frame.copy()
            
            if frame_copy is None:
                time.sleep(0.1)
                continue
            
            d = self.display
            if d["box"] is not None:
                cv2.polylines(frame_copy, [d["box"]], True, (0, 255, 0), 3)
            
            cv2.rectangle(frame_copy, (0,0), (640, 70), (0,0,0), -1)
            cv2.putText(frame_copy, str(d["plate"]), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, d["color"], 2)
            cv2.putText(frame_copy, str(d["info"]), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
            
            ret, buf = cv2.imencode('.jpg', frame_copy)
            if ret:
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
