import sqlite3
import hashlib
from datetime import datetime

# ==========================================
# 1. CLASSE USER 
# ==========================================
class User:
    def __init__(self, id=None, badges=None, plaques=None, nom="", role="USER", 
                 password="", tel="", adresse="", email=""):
        self.id = id
        self.badges = badges if badges else [] # Liste de badges
        self.plaques = plaques if plaques else [] # Liste de plaques
        self.nom = nom
        self.role = role
        self.password = password
        self.tel = tel
        self.adresse = adresse
        self.email = email

    # Propriétés pour Flask-Login
    @property
    def is_active(self): return True
    @property
    def is_authenticated(self): return True
    @property
    def is_anonymous(self): return False
    def get_id(self): return str(self.id)

    # Helpers pour l'affichage (concaténation avec virgules)
    @property
    def plaques_str(self): return ", ".join(self.plaques)
    @property
    def badges_str(self): return ", ".join(self.badges)

    def __repr__(self):
        return f"<User {self.nom}>"

# ==========================================
# 2. MANAGER BASE DE DONNÉES
# ==========================================
class DbManager:
    def __init__(self, db_path="parking.db"):
        self.db_path = db_path
        self.init_db()

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row 
        return conn

    def _row_to_user(self, row):
        """Convertit une ligne SQL en objet User avec ses plaques et badges"""
        if not row: return None
        user = User(
            id=row['id'],
            nom=row['nom'],
            role=row['role'],
            password=row['password'],
            tel=row['tel'],
            adresse=row['adresse'],
            email=row['email']
        )
        user.plaques = self.get_plaques_by_user_id(user.id)
        user.badges = self.get_badges_by_user_id(user.id)
        return user

    def init_db(self):
        with self.connect() as conn:
            c = conn.cursor()
            
            # 1. Table Historique
            c.execute('''CREATE TABLE IF NOT EXISTS historique (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plaque TEXT NOT NULL,
                        entree TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        sortie TIMESTAMP,
                        etat TEXT DEFAULT 'GARÉ')''')
            
            # 2. Table Users
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        id_badge TEXT, 
                        nom TEXT,
                        role TEXT DEFAULT 'USER',
                        password TEXT,
                        tel TEXT,
                        adresse TEXT,
                        email TEXT)''')
            
            # 3. Table Plaques
            c.execute('''CREATE TABLE IF NOT EXISTS plaques (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        numero TEXT UNIQUE,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )''')

            # 4. Table Badges
            c.execute('''CREATE TABLE IF NOT EXISTS badges (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        uid TEXT UNIQUE,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )''')
            
            # Admin par défaut
            c.execute("SELECT * FROM users WHERE nom = 'admin'")
            if not c.fetchone():
                pwd_hash = hashlib.sha256("admin123".encode()).hexdigest()
                admin = User(nom="admin", role="IT", password=pwd_hash)
                self.ajouter_user(admin)
                print("--- ADMIN PAR DÉFAUT CRÉÉ ---")
            
            conn.commit()

    # ==========================================
    # GESTION DES LISTES (PLAQUES & BADGES)
    # ==========================================

    def get_items_by_user(self, table, user_id, col_name):
        """Récupère une liste d'éléments (plaques ou badges) pour un user"""
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute(f"SELECT {col_name} FROM {table} WHERE user_id = ?", (user_id,))
                return [row[0] for row in c.fetchall()]
        except: return []

    def get_plaques_by_user_id(self, user_id):
        return self.get_items_by_user('plaques', user_id, 'numero')

    def get_badges_by_user_id(self, user_id):
        return self.get_items_by_user('badges', user_id, 'uid')

    def update_user_list(self, table, col_name, user_id, items_list):
        """Met à jour une liste (supprime tout et recrée)"""
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
                for item in items_list:
                    item_clean = item.strip().upper()
                    if item_clean:
                        c.execute(f"INSERT OR IGNORE INTO {table} (user_id, {col_name}) VALUES (?, ?)", (user_id, item_clean))
                conn.commit()
            return True
        except Exception as e:
            print(f"Err update {table}: {e}")
            return False

    # ==========================================
    # CRUD UTILISATEUR
    # ==========================================

    def ajouter_user(self, user: User):
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute("""INSERT INTO users (nom, role, password, tel, adresse, email) 
                             VALUES (?, ?, ?, ?, ?, ?)""",
                          (user.nom, user.role, user.password, user.tel, user.adresse, user.email))
                user_id = c.lastrowid
                conn.commit()
            
            if user_id:
                if user.plaques: self.update_user_list('plaques', 'numero', user_id, user.plaques)
                if user.badges: self.update_user_list('badges', 'uid', user_id, user.badges)
            return True
        except Exception as e:
            print(f"[DB] Erreur ajout: {e}")
            return False

    def update_user_info(self, user_id, nom, role, plaques_list, badges_list, email, tel):
        """Mise à jour Admin : Infos + Plaques + Badges"""
        try:
            with self.connect() as conn:
                c = conn.cursor()
                # On ne met plus à jour id_badge dans la table users car on utilise la table badges
                c.execute("UPDATE users SET nom=?, role=?, email=?, tel=? WHERE id=?", 
                          (nom, role, email, tel, user_id))
                conn.commit()
            
            self.update_user_list('plaques', 'numero', user_id, plaques_list)
            self.update_user_list('badges', 'uid', user_id, badges_list)
            return True
        except Exception as e:
            print(f"[DB] Erreur update: {e}")
            return False
    
    def update_self_profile(self, user_id, email, tel, new_password=None):
        """Mise à jour par l'utilisateur lui-même (Profil)"""
        try:
            with self.connect() as conn:
                c = conn.cursor()
                if new_password:
                    pwd_hash = hashlib.sha256(new_password.encode()).hexdigest()
                    c.execute("UPDATE users SET email=?, tel=?, password=? WHERE id=?", (email, tel, pwd_hash, user_id))
                else:
                    c.execute("UPDATE users SET email=?, tel=? WHERE id=?", (email, tel, user_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"[DB] Erreur update profile: {e}")
            return False

    def delete_user_by_id(self, user_id):
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM plaques WHERE user_id=?", (user_id,))
                c.execute("DELETE FROM badges WHERE user_id=?", (user_id,))
                c.execute("DELETE FROM users WHERE id=?", (user_id,))
                conn.commit()
                return True
        except: return False

    def get_all_users(self):
        """Récupère tous les utilisateurs avec leurs plaques et badges concaténés"""
        try:
            with self.connect() as conn:
                c = conn.cursor()
                sql = """
                SELECT u.id, u.nom, u.role, u.email, u.tel, 
                       GROUP_CONCAT(DISTINCT p.numero) as plaques_str,
                       GROUP_CONCAT(DISTINCT b.uid) as badges_str
                FROM users u
                LEFT JOIN plaques p ON u.id = p.user_id
                LEFT JOIN badges b ON u.id = b.user_id
                GROUP BY u.id
                ORDER BY u.id DESC
                """
                c.execute(sql)
                res = []
                for row in c.fetchall():
                    d = dict(row)
                    d['plaques_str'] = d['plaques_str'].replace(',', ', ') if d['plaques_str'] else ""
                    d['badges_str'] = d['badges_str'].replace(',', ', ') if d['badges_str'] else ""
                    res.append(d)
                return res
        except Exception as e:
            print(f"Err all users: {e}")
            return []

    # ==========================================
    # AUTHENTIFICATION & RECHERCHE
    # ==========================================

    def verifier_login(self, username, password):
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE nom = ? AND password = ?", (username, pwd_hash))
            return self._row_to_user(c.fetchone())

    def get_user_by_id(self, user_id):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return self._row_to_user(c.fetchone())

    def get_user_by_plaque(self, plaque):
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute("SELECT user_id FROM plaques WHERE numero = ?", (plaque,))
                row = c.fetchone()
                if row: return self.get_user_by_id(row[0])
                return None
        except: return None

    # ==========================================
    # RFID & BADGES
    # ==========================================

    def verifier_badge(self, uid_badge):
        """Vérifie si un badge existe et renvoie le nom du propriétaire"""
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT u.nom 
                    FROM users u 
                    JOIN badges b ON u.id = b.user_id 
                    WHERE b.uid = ?""", (uid_badge,))
                data = c.fetchone()
                return data['nom'] if data else None
        except Exception as e: return None

    def creer_badge_rapide(self, uid_badge):
        """Création d'un user à la volée via badge inconnu (optionnel)"""
        try:
            user = User(badges=[uid_badge], nom=f"User_{uid_badge[-4:]}")
            return self.ajouter_user(user)
        except Exception as e:
            print(f"[DB ERROR] Création rapide : {e}")
            return False

    # ==========================================
    # LOGIQUE PARKING & HISTORIQUE
    # ==========================================

    def process_entree(self, plaque):
        with self.connect() as conn:
            c = conn.cursor()
            # Vérifie si déjà garé
            c.execute("SELECT id, entree FROM historique WHERE plaque = ? AND etat = 'GARÉ'", (plaque,))
            data = c.fetchone()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if data: return f"Deja la ({str(data['entree']).split(' ')[1]})"
            
            c.execute("INSERT INTO historique (plaque, etat, entree) VALUES (?, 'GARÉ', ?)", (plaque, now))
            conn.commit()
            
            user = self.get_user_by_plaque(plaque)
            return f"Salut {user.nom} !" if user else "Bienvenue !"

    def process_sortie(self, plaque):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT id, entree FROM historique WHERE plaque = ? AND etat = 'GARÉ'", (plaque,))
            data = c.fetchone()
            if data:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("UPDATE historique SET sortie = ?, etat = 'PARTI' WHERE id = ?", (now, data['id']))
                conn.commit()
                return "Au revoir !"
            return "Pas trouve"

    def get_last_entry(self, plaque):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT entree, etat FROM historique WHERE plaque = ? ORDER BY id DESC LIMIT 1", (plaque,))
            row = c.fetchone()
            return dict(row) if row else None

    def get_full_user_history(self, plaques_list):
        if not plaques_list: return []
        try:
            with self.connect() as conn:
                c = conn.cursor()
                placeholders = ','.join('?' * len(plaques_list))
                sql = f"SELECT plaque, entree, sortie, etat FROM historique WHERE plaque IN ({placeholders}) ORDER BY entree ASC"
                c.execute(sql, tuple(plaques_list))
                return [dict(row) for row in c.fetchall()]
        except: return []

    def close(self):
        pass