import sys
import os
import cv2
import numpy as np
import time
import hashlib
from datetime import datetime
from flask import Flask, Response, jsonify, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import json

# --- 1. SETUP DES CHEMINS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.join(current_dir, '..')
sys.path.append(root_dir)
template_dir = os.path.join(root_dir, 'templates')

from src.db_manager import DbManager, User

# --- 2. CONFIG FLASK ---
app = Flask(__name__, template_folder=template_dir)
app.secret_key = 'CLE_DE_TEST_SECRET'

# --- 3. INIT DB & LOGIN ---
db = DbManager(os.path.join(root_dir, "parking.db"))
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Création d'un utilisateur TEST "Conducteur" si inexistant
def init_test_data():
    # 1. Création du User si inexistant
    if not db.verifier_login("driver", "user123"):
        print("--- Création utilisateur test : driver / user123 ---")
        pwd_hash = hashlib.sha256("user123".encode()).hexdigest()
        u = User(nom="driver", role="USER", password=pwd_hash, plaques=["AA-123-BB", "ZZ-999-TOP"], id_badge="TEST_BADGE")
        db.ajouter_user(u)
    
    # 2. IMPORTANT : On force l'entrée de la voiture TEST à chaque démarrage du serveur
    # Cela garantit que sur le Dashboard, elle apparaisse en VERT (GARÉ)
    print("--- Simulation : Entrée de AA-123-BB ---")
    db.process_entree("AA-123-BB")

init_test_data()

@login_manager.user_loader
def load_user(user_id):
    return db.get_user_by_id(user_id)

# --- 4. ROUTES AUTHENTIFICATION ---

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
            flash('Identifiants invalides (Essayez: admin/admin123 ou driver/user123)')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- 5. ROUTE DASHBOARD ---

@app.route('/')
@login_required
def index():
    vehicles_data = []
    calendar_data = {} # Dictionnaire pour le calendrier
    
    if current_user.role == 'USER':
        # 1. Gestion des cartes véhicules (Code existant amélioré)
        # ... (Garde ton code existant pour vehicles_data ici) ...
        # (Je remets le code existant pour rappel contextuel, mais concentre-toi sur la suite)
        for plaque in current_user.plaques:
            info = db.get_last_entry(plaque)
            if info:
                 # ... (Ton code de traitement date/durée existant) ...
                 # Juste pour l'exemple je remets le minimum
                 raw_date = str(info['entree'])
                 try:
                    dt_entree = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
                    info['date_affichee'] = dt_entree.strftime("le %d-%m-%Y à %H:%M:%S")
                    if info['etat'] == 'GARÉ':
                        delta = datetime.now() - dt_entree
                        minutes = int(delta.total_seconds() / 60)
                        info['duree_txt'] = f"{int(minutes/60)}h{minutes%60:02d}"
                    else:
                        info['duree_txt'] = ""
                 except: pass
                 info['numero'] = plaque
                 vehicles_data.append(info)
            else:
                 vehicles_data.append({'numero': plaque, 'etat': 'INCONNU', 'date_affichee': '-', 'duree_txt': ''})

        # 2. GESTION DU CALENDRIER (NOUVEAU)
        raw_history = db.get_full_user_history(current_user.plaques)
        
        for row in raw_history:
            try:
                # Conversion dates
                dt_in = datetime.strptime(str(row['entree']), "%Y-%m-%d %H:%M:%S")
                date_key = dt_in.strftime("%Y-%m-%d") # ex: "2026-01-25"
                
                # Calcul Durée
                if row['sortie']:
                    dt_out = datetime.strptime(str(row['sortie']), "%Y-%m-%d %H:%M:%S")
                    duration = dt_out - dt_in
                    heure_sortie = dt_out.strftime("%H:%M")
                else:
                    duration = datetime.now() - dt_in
                    heure_sortie = "En cours"
                
                # Formatage texte durée (ex: 02:15:00)
                total_seconds = int(duration.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                duree_str = f"{hours}h {minutes}min"

                # Création du texte HTML pour le tooltip
                info_html = f"<div><strong>{row['plaque']}</strong><br>Entrée : {dt_in.strftime('%H:%M')}<br>Sortie : {heure_sortie}<br>Temps : {duree_str}</div><hr style='margin:2px 0; border-color:#555'>"

                # On ajoute au dictionnaire (on concatène si plusieurs entrées le même jour)
                if date_key in calendar_data:
                    calendar_data[date_key] += info_html
                else:
                    calendar_data[date_key] = info_html

            except Exception as e:
                print(f"Erreur date calendrier: {e}")

    return render_template('dashboard.html', 
                           user=current_user, 
                           vehicles=vehicles_data, 
                           badges=current_user.badges,
                           calendar_data=json.dumps(calendar_data))


# --- 6. SIMULATION API (Backend Admin) ---

# API LISTE USERS
@app.route('/api/users')
@login_required
def get_users_list():
    if current_user.role != 'IT': return jsonify([])
    return jsonify(db.get_all_users())

# API AJOUT USER
@app.route('/api/add_user', methods=['POST'])
@login_required
def add_user_api():
    if current_user.role != 'IT': return jsonify({"success": False})
    data = request.json
    try:
        pwd_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        
        # Traitement Plaques
        plaques_raw = data.get('plaque', '')
        plaques_list = [p.strip() for p in plaques_raw.split(',') if p.strip()]

        # Traitement Badges (NOUVEAU)
        badges_raw = data.get('badge', '')
        badges_list = [b.strip() for b in badges_raw.split(',') if b.strip()]

        new_user = User(
            nom=data['nom'],
            role=data['role'],
            password=pwd_hash,
            plaques=plaques_list,
            badges=badges_list, # On passe la liste
            email=data['email'],
            tel=data.get('tel', '')
        )
        if db.ajouter_user(new_user): return jsonify({"success": True})
        else: return jsonify({"success": False, "msg": "Erreur DB"})
    except Exception as e: return jsonify({"success": False, "msg": str(e)})

# API UPDATE USER
@app.route('/api/update_user', methods=['POST'])
@login_required
def update_user_api():
    if current_user.role != 'IT': return jsonify({"success": False})
    data = request.json
    
    plaques_raw = data.get('plaque', '')
    plaques_list = [p.strip() for p in plaques_raw.split(',') if p.strip()]

    badges_raw = data.get('badge', '')
    badges_list = [b.strip() for b in badges_raw.split(',') if b.strip()]

    success = db.update_user_info(
        data['id'], data['nom'], data['role'], 
        plaques_list,
        badges_list, # On passe la liste
        data['email'],
        data.get('tel', '')
    )
    return jsonify({"success": success})

# API DELETE USER
@app.route('/api/delete_user', methods=['POST'])
@login_required
def delete_user_api():
    if current_user.role != 'IT': return jsonify({"success": False, "msg": "Interdit"})
    data = request.json
    success = db.delete_user_by_id(data['id'])
    return jsonify({"success": success})

@app.route('/api/mqtt_logs')
@login_required
def get_mqtt_logs():
    return jsonify(["[AUTO] Système Prêt", "[AUTO] DB Connectée"])

@app.route('/api/json')
@login_required
def get_json():
    try:
        with db.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM historique ORDER BY id DESC LIMIT 10")
            return jsonify([dict(r) for r in c.fetchall()])
    except: return jsonify([])

# --- 7. SIMULATION VIDEO ---
def generate_mock_video(text_label, color):
    width, height = 640, 480
    img = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.rectangle(img, (0,0), (width, height), color, 5)
    cv2.putText(img, f"LIVE {text_label}", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
    ret, buffer = cv2.imencode('.jpg', img)
    frame = buffer.tobytes()
    while True:
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(1)

@app.route('/api/update_profile', methods=['POST'])
@login_required
def update_profile_api():
    data = request.json
    
    # On récupère l'ID de l'utilisateur connecté
    user_id = current_user.id
    email = data.get('email', '')
    tel = data.get('tel', '')
    password = data.get('password', '') # Peut être vide si pas de changement
    
    success = db.update_self_profile(user_id, email, tel, password if password else None)
    return jsonify({"success": success})

@app.route('/vid_in')
@login_required
def vid_in():
    if current_user.role != 'IT': return "Interdit", 403
    return Response(generate_mock_video("ENTREE", (0, 100, 0)), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/vid_out')
@login_required
def vid_out():
    if current_user.role != 'IT': return "Interdit", 403
    return Response(generate_mock_video("SORTIE", (0, 0, 100)), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/control', methods=['POST'])
@login_required
def control_hardware():
    if current_user.role != 'IT': return jsonify({"success": False, "msg": "Interdit"})
    
    data = request.json
    action_type = data.get('type')
    
    try:
        # --- 1. GESTION BARRIÈRES ---
        if action_type == 'barrier':
            gate = data.get('gate') # 'in' ou 'out'
            cmd = data.get('cmd')   # 'OPEN' ou 'CLOSE'
            
            print(f"⚡ [COMMANDE MANUELLE] Barrière {gate.upper()} -> {cmd}")
            
            # NOTE POUR LE VRAI MAIN.PY :
            # topic = f"parking/barrier_{0 if gate=='in' else 1}/state"
            # mqtt.publish(topic, cmd) 

        # --- 2. GESTION LCD ---
        elif action_type == 'lcd':
            text = data.get('text', '')
            print(f"📟 [COMMANDE MANUELLE] LCD Message : {text}")
            
            # NOTE POUR LE VRAI MAIN.PY :
            # lcd.clear()
            # lcd.scroll_text(text)

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})

if __name__ == '__main__':
    print("--- SERVEUR DE TEST ---")
    print("http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)