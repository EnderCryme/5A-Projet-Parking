import paho.mqtt.client as mqtt
import time
from datetime import datetime

class MqttManager:
    def __init__(self, db_manager=None, logs_list=None, broker="localhost", port=1883, topic_racine="parking"):
        self.client = mqtt.Client()
        self.topic_racine = topic_racine
        self.db = db_manager
        self.logs = logs_list if logs_list is not None else [] # Référence vers la liste des logs du Main
        
        # Variable pour stocker l'heure du dernier badge valide (pour la caméra)
        self.last_unlock_time = 0 
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        try:
            self.client.connect(broker, port, 60)
            self.client.loop_start()
            print(f"[MQTT] Connecté au broker {broker}")
        except:
            print("[MQTT] ❌ Erreur connexion (Mosquitto est lancé ?)")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            # On écoute RFID ET tout le reste pour les logs du site web
            client.subscribe("RFID/#")
            client.subscribe(f"{self.topic_racine}/#")
            print("[MQTT] Abonné aux canaux")
        else:
            print(f"[MQTT] Échec connexion code: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8")
            
            # --- 1. LOGGING POUR LE SITE WEB ---
            t = datetime.now().strftime("%H:%M:%S")
            self.logs.insert(0, f"[{t}] {topic} : {payload}")
            if len(self.logs) > 30: self.logs.pop() # On garde les 30 derniers
            
            # Si pas de DB, on arrête là pour la logique métier
            if self.db is None: return

            # --- 2. LOGIQUE RFID ---
            if topic == "RFID/ID":
                print(f"[RFID] Vérification badge : {payload}")
                if hasattr(self.db, 'verifier_badge'):
                    nom_user = self.db.verifier_badge(payload)
                    if nom_user:
                        print(f"   => ACCES AUTORISÉ : {nom_user}")
                        
                        # IMPORTANT : On enregistre l'heure pour que la Caméra le voie
                        self.last_unlock_time = time.time()
                        
                        # On dit à l'Arduino/STM32 d'afficher "Badge OK" (mais pas ouvrir direct)
                        client.publish("RFID/CMD", "UNLOCK_READY") 
                    else:
                        print("   => ACCES REFUSÉ")
                        client.publish("RFID/CMD", "DENY")

            elif topic == "RFID/ADD":
                if hasattr(self.db, 'creer_badge_rapide') and self.db.creer_badge_rapide(payload):
                    client.publish("RFID/CMD", "ADDED")
                else:
                    client.publish("RFID/CMD", "ERROR_DB")

            elif topic == "RFID/DEL":
                if hasattr(self.db, 'supprimer_par_badge') and self.db.supprimer_par_badge(payload):
                    client.publish("RFID/CMD", "DELETED")
                else:
                    client.publish("RFID/CMD", "ERROR_DB")

        except Exception as e:
            print(f"[MQTT] Erreur lecture message: {e}")

    def publish(self, sous_topic, message):
        """Publie sur parking/sous_topic"""
        try:
            full_topic = f"{self.topic_racine}/{sous_topic}"
            self.client.publish(full_topic, message)
        except: pass

    # Nouvelle méthode pour que le Main.py vérifie si un badge a été passé récemment
    def is_unlock_active(self, timeout=15.0):
        return (time.time() - self.last_unlock_time) < timeout

    def close(self):
        self.client.loop_stop()
        self.client.disconnect()