# 🧪 Environnement de Test & Simulation

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

### B. Lancer le Site Web de Test (`test_server_render.py`)
Lance une version "Mock" du serveur. C'est exactement comme le `main.py`, mais les caméras sont remplacées par des images générées par ordinateur.

* **Utilité :** Travailler sur le HTML/CSS (`templates/`) sans lancer la reconnaissance d'image.
* **Accès :** Ouvre `http://192.168.78.2:5000/` dans ton navigateur.

**Commande :**
```bash
python3 test_server_render.py
