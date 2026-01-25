import os
import sys
import sqlite3
import hashlib
import random
from datetime import datetime, timedelta

# --- IMPORT DU DB_MANAGER ---
# On ajoute le dossier courant au path pour trouver les modules
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.join(current_dir, '..')
sys.path.append(root_dir)
from src.db_manager import DbManager, User

# --- CONFIGURATION ---
DB_FILE = "parking.db"
TARGET_DATE = datetime(2026, 1, 25, 12, 0, 0) # On simule qu'il est midi le 25 Janvier
START_DATE = TARGET_DATE - timedelta(days=10) # On commence 10 jours avant

def reset_db():
    """Supprime la DB existante"""
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"🗑️  Ancienne base de données '{DB_FILE}' supprimée.")
    else:
        print(f"🆕 Aucune base trouvée, création d'une nouvelle.")

def generate_history(db):
    print("⏳ Génération de l'historique sur 10 jours...")
    
    # --- 1. CRÉATION DES UTILISATEURS ---
    users_data = [
        {
            "nom": "admin", "role": "IT", "pass": "admin123", 
            "plaques": ["ADM-001", "IT-999-TEST"], "tel": "06.00.00.00.01", "email": "admin@parking.com"
        },
        {
            "nom": "Pierre", "role": "USER", "pass": "pierre123", 
            "plaques": ["AA-123-BB"], "tel": "06.12.34.56.78", "email": "pierre@mail.com"
        },
        {
            "nom": "Sophie", "role": "USER", "pass": "sophie123", 
            "plaques": ["SO-777-PH", "XX-000-XX"], "tel": "07.98.76.54.32", "email": "sophie@mail.com"
        }
    ]

    users_objs = []
    for u in users_data:
        pwd_hash = hashlib.sha256(u["pass"].encode()).hexdigest()
        new_user = User(
            nom=u["nom"], role=u["role"], password=pwd_hash, 
            plaques=u["plaques"], tel=u["tel"], email=u["email"], id_badge=f"BADGE_{u['nom'].upper()}"
        )
        db.ajouter_user(new_user)
        users_objs.append(new_user)
        print(f"👤 Utilisateur créé : {u['nom']} ({len(u['plaques'])} plaques)")

    # --- 2. SIMULATION ENTRÉES / SORTIES ---
    
    total_entries = 0
    
    with db.connect() as conn:
        c = conn.cursor()
        
        # On boucle sur chaque jour du 15 au 25 Janvier
        for day_offset in range(11): # 0 à 10
            current_day = START_DATE + timedelta(days=day_offset)
            is_today = (current_day.date() == TARGET_DATE.date())
            
            print(f"📅 Traitement du {current_day.strftime('%d/%m/%Y')}...")

            for user in users_objs:
                # Chaque utilisateur a une probabilité de venir travailler ce jour-là (ex: 80% sauf le dimanche)
                if current_day.weekday() == 6 and random.random() > 0.1: continue # Dimanche, peu de chance
                if random.random() < 0.2: continue # 20% de chance d'absence aléatoire
                
                # Choix d'une plaque au hasard parmi celles de l'utilisateur
                plaque = random.choice(user.plaques)
                
                # Heure d'entrée aléatoire (entre 07h00 et 10h30)
                hour_in = random.randint(7, 10)
                minute_in = random.randint(0, 59)
                dt_in = current_day.replace(hour=hour_in, minute=minute_in, second=0)
                
                # Heure de sortie aléatoire (entre 16h00 et 19h30) ou PAUSE DEJEUNER
                duration_hours = random.randint(4, 9)
                dt_out = dt_in + timedelta(hours=duration_hours, minutes=random.randint(0, 59))
                
                # FORMATAGE SQL
                str_in = dt_in.strftime("%Y-%m-%d %H:%M:%S")
                str_out = dt_out.strftime("%Y-%m-%d %H:%M:%S")
                
                # CAS SPÉCIAL : AUJOURD'HUI (25 Janvier)
                if is_today:
                    # Pierre est arrivé ce matin et est toujours garé
                    if user.nom == "Pierre":
                        c.execute("INSERT INTO historique (plaque, entree, etat) VALUES (?, ?, 'GARÉ')", (plaque, str_in))
                        print(f"   -> 🟢 {user.nom} ({plaque}) est entré à {str_in} et est ACTUELLEMENT GARÉ.")
                    
                    # Sophie est venue mais est repartie tôt (ex: urgence ou demi-journée)
                    elif user.nom == "Sophie":
                        early_out = dt_in + timedelta(hours=2)
                        str_early_out = early_out.strftime("%Y-%m-%d %H:%M:%S")
                        c.execute("INSERT INTO historique (plaque, entree, sortie, etat) VALUES (?, ?, ?, 'PARTI')", (plaque, str_in, str_early_out))
                        print(f"   -> 🟠 {user.nom} ({plaque}) est passé (Entrée: {str_in} / Sortie: {str_early_out})")
                    
                    # Admin ne vient pas aujourd'hui (ou n'est pas encore arrivé)
                    else:
                        pass 

                # CAS NORMAL (Jours passés)
                else:
                    # On insère une entrée terminée (PARTI)
                    c.execute("INSERT INTO historique (plaque, entree, sortie, etat) VALUES (?, ?, ?, 'PARTI')", 
                              (plaque, str_in, str_out))
                    total_entries += 1

        conn.commit()
    
    print("------------------------------------------------")
    print(f"✅ Simulation terminée. {total_entries} entrées historiques générées.")
    print(f"✅ Date simulée : {TARGET_DATE.strftime('%d/%m/%Y à %H:%M')}")

if __name__ == "__main__":
    # 1. Reset
    reset_db()
    
    # 2. Init DB Manager (ça recrée les tables vides)
    db_manager = DbManager(DB_FILE)
    
    # 3. Remplissage
    generate_history(db_manager)