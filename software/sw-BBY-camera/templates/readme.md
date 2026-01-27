# Interface Web (Templates)

![Tech](https://img.shields.io/badge/Tech-HTML5%20%7C%20CSS3%20%7C%20JS-orange)
![Engine](https://img.shields.io/badge/Render-Jinja2%20(Flask)-black)
![Style](https://img.shields.io/badge/Theme-Dark%20Mode-333)

## 📖 Vue d'ensemble

Ce dossier contient les fichiers HTML utilisés par le serveur Flask pour générer l'interface utilisateur.
L'interface est conçue en **Dark Mode** natif pour limiter la fatigue visuelle et utilise du **JavaScript pur (Vanilla JS)** pour les mises à jour dynamiques (AJAX) sans rechargement de page.

---

## 📂 Détail des Vues

### 1. Portail de Connexion (`login.html`)
Point d'entrée sécurisé de l'application.

* **Fonctionnalités :**
    * Formulaire d'authentification (Utilisateur / Admin).
    * Bouton "Afficher/Masquer" le mot de passe.
    * Modale "Mot de passe oublié" (Simulation frontend).
* **Design :** Carte centrée avec ombres portées et design épuré `Segoe UI`.

### 2. Console Administrateur (`index.html`)
Le centre de contrôle pour l'équipe IT (`role: IT`).

* **Supervision Temps Réel :**
    * **Vidéosurveillance :** Affiche les flux des caméras Entrée/Sortie (simulés ou réels).
    * **Logs MQTT :** Console défilante affichant les événements système (Passage de badge, Ouverture barrière).
* **Historique Global :** Tableau complet des mouvements avec une barre de défilement verticale pour naviguer dans les archives.
* **Technique :** Utilise `setInterval` et `fetch` pour rafraîchir les données toutes les secondes.

### 3. Espace Conducteur (`dashboard.html`)
L'interface personnelle pour les utilisateurs finaux (`role: USER`).

* **Gestion Flotte :** Affiche les véhicules de l'utilisateur sous forme de cartes.
    * Indique l'état actuel : **GARÉ** (Vert) ou **SORTI** (Orange).
    * Calcule la durée de stationnement en temps réel.
* **Calendrier Visuel :** Historique personnel affiché sous forme de calendrier interactif (les jours d'activité sont cliquables).
* **Profil :** Modale permettant de mettre à jour son email et son numéro de téléphone via une API REST.

---

## ⚙️ Comment tester ces interfaces ?

Ces fichiers ne peuvent pas être ouverts directement dans un navigateur (le code `{{ variable }}` ne fonctionnerait pas).

Pour les visualiser, lancez le serveur de rendu dans le dossier `test/` :

```bash
cd ../test
python3 test_server_render.py

