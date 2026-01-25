import paho.mqtt.client as mqtt
from dataBase import DbManager  # <--- CORRECTION ICI (Majuscule B)
import time

# --- CONFIGURATION ---
BROKER_ADDRESS = "192.168.78.2" # Ton PC
BROKER_PORT = 1883

# Initialisation de TA base
# Assure-toi que le chemin "/home/vcauq/parking.db" est bon
db = DbManager("/home/vcauq/parking.db") 

def on_connect(client, userdata, flags, rc):
    """Fonction appelée quand le script se connecte au broker"""
    if rc == 0:
        print("✅ Connecté au Broker MQTT !")
        # On s'abonne à tous les topics qui commencent par RFID/
        client.subscribe("RFID/#") 
    else:
        print(f"❌ Echec connexion, code retour : {rc}")

def on_message(client, userdata, msg):
    """Fonction appelée à chaque message reçu"""
    topic = msg.topic
    
    # On décode le message (qui arrive en bytes) en string
    try:
        payload = msg.payload.decode("utf-8")
    except:
        print("Erreur de décodage payload")
        return

    print(f"\uD83D\uDCE9 Reçu sur {topic} : {payload}")

    # --- 1. DEMANDE D'ACCES ---
    if topic == "RFID/ID":
        print(f"\uD83D\uDD0D Vérification badge : {payload}...")
        
        # Appel à ta méthode SQL
        nom_user = db.verifier_badge(payload)
        
        if nom_user:
            print(f"   => ACCES AUTORISÉ : {nom_user}")
            client.publish("RFID/CMD", "UNLOCK")
        else:
            print("   => ACCES REFUSÉ (Inconnu)")
            client.publish("RFID/CMD", "DENY")

    # --- 2. MODE AJOUT (Admin) ---
    elif topic == "RFID/ADD":
        print(f"➕ Demande d'ajout badge : {payload}")
        if db.creer_badge_rapide(payload):
            print("   => Ajouté avec succès dans SQL")
            client.publish("RFID/CMD", "ADDED")
        else:
            print("   => Erreur ajout (Déjà existant ?)")
            client.publish("RFID/CMD", "ERROR_DB")

    # --- 3. MODE SUPPRESSION (Admin) ---
    elif topic == "RFID/DEL":
        print(f"\uD83D\uDDD1️ Demande suppression badge : {payload}")
        if db.supprimer_par_badge(payload):
            print("   => Supprimé avec succès de SQL")
            client.publish("RFID/CMD", "DELETED")
        else:
            print("   => Erreur suppression (Inexistant ?)")
            client.publish("RFID/CMD", "ERROR_DB")

# --- MAIN LOOP ---
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("⏳ Connexion au broker MQTT...")
try:
    client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
    # Boucle infinie qui attend les messages
    client.loop_forever()
except Exception as e:
    print(f"CRASH: Impossible de se connecter au broker : {e}")
