# Environnement de Test & Simulation

![Type](https://img.shields.io/badge/Type-Unit%20Tests-green)
![Mode](https://img.shields.io/badge/Mode-Simulation%20%26%20Hardware-blue)
![Coverage](https://img.shields.io/badge/Coverage-Drivers%20%2B%20Web-orange)

## 📖 À quoi sert ce dossier ?

Ce dossier contient des outils pour vérifier que ton projet fonctionne correctement, que ce soit sur ton **PC (Simulation)** ou sur la **BeagleBone (Réel)**.

---

## 🚀 1. Simulation sur PC (Sans matériel)

Utilise ces scripts pour tester l'interface graphique et la logique sans avoir besoin des caméras ou des capteurs.

### A. Générer un historique fictif (`populate_db.py`)
Ce script est **indispensable pour la démo**. Il remplit la base de données avec 10 jours d'entrées/sorties réalistes pour que le Dashboard ne soit pas vide.

* **Crée les utilisateurs :** `admin` (Mdp: `admin123`) et `driver` (Mdp: `user123`).
* **Simule l'activité :** Génère des mouvements de véhicules et place certains véhicules en état "GARÉ" pour tester l'affichage temps réel.

**Commande :**
```bash
python3 populate_db.py
```
### B. Lancer le Site Web de Test (`test_server_render.py`)
Lance une version "Mock" du serveur. C'est exactement comme le `main.py`, mais les caméras sont remplacées par des images générées par ordinateur.

* **Utilité :** Travailler sur le HTML/CSS (`templates/`) sans lancer la reconnaissance d'image.
* **Accès :** Ouvre `http://192.168.78.2:5000/` dans ton navigateur.

**Commande :**
```bash
python3 test_server_render.py
```
### 🎨 Interfaces Web à Tester

Une fois le serveur lancé, tu peux tester les écrans suivants (situés dans `../templates/`) :

* **Connexion (`login.html`) :**
    * **Admin :** Login `admin` / Pass `admin123`
    * **User :** Login `driver` / Pass `user123`
* **Dashboard Conducteur (`dashboard.html`) :**
    * Accessible avec le compte `driver`.
    * Affiche l'état des véhicules (**Vert** = Garé / **Orange** = Sorti).
    * Affiche l'historique personnel sous forme de calendrier interactif.
* **Console Admin (`index.html`) :**
    * Accessible avec le compte `admin`.
    * Affiche les flux vidéo simulés et les logs MQTT en temps réel.

---

## 🛠 2. Tests Matériels (Sur BeagleBone)

Lance ces scripts directement sur la carte pour valider les composants physiques individuellement.

| Fichier | Matériel testé | Description |
| :--- | :--- | :--- |
| `test_lcd_manager.py` | Écran LCD | Affiche "TEST" fixe puis fait défiler "BRAVO". |
| `test_sensor_manager.py` | Capteur BME680 | Lit et affiche la température/humidité dans la console. |
| `test_camera_manager.py` | Webcam & IA | Lance un flux vidéo avec détection de plaques (carrés verts). |
| `test_db_manager.py` | SQLite | Teste la création, lecture et suppression d'un utilisateur. |

**Exemple d'utilisation :**

```bash
# Pour tester l'écran LCD
python3 test_lcd_manager.py



