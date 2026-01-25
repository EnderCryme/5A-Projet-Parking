import sys
import os
from flask import Flask, Response

# On ajoute le dossier src au chemin pour trouver la classe
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.camera_manager import CameraManager

# --- CONFIG TEST ---
CAM_ID = 1  # Ta caméra d'entrée

app = Flask(__name__)
manager = None

def callback_test(plaque, role):
    print(f"\n✅ [TEST REUSSI] Plaque validée : {plaque}")

def gen():
    return manager.generate_jpeg()

@app.route('/')
def index():
    return f"""
    <body style='background:black; text-align:center; color:white'>
        <h1>TEST CAMERA MANAGER (XML AUTO)</h1>
        <p>Doit afficher l'image + Carré Jaune/Vert</p>
        <img src='/video' style='border:2px solid green; width:640px'>
    </body>
    """

@app.route('/video')
def video():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("--- TEST CAMERA MANAGER ---")
    
    # On instancie la classe (elle va chercher le XML toute seule)
    manager = CameraManager(camera_id=CAM_ID, role="test", callback_detection=callback_test)
    manager.start()
    
    print("Web: http://0.0.0.0:5000")
    try:
        app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
    finally:
        manager.stop()
