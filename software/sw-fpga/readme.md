# Historique des Versions - Contrôleur de Barrière MQTT

> La compilation est cross-compiler : 
> ```bash ~/parking_fpga/buildroot/output/host/bin/riscv32-buildroot-linux-gnu-gcc v4.c -o v4 -march=rv32ima -mabi=ilp32 -lmosquitto ```


---

## v0 : Version Initiale (Preuve de Concept)
*Fichier source : `v0-test-concept.c`*

C'est la version de base pour valider le fonctionnement du moteur et du protocole MQTT.

* **Gestion Unique :** Ne contrôle qu'une seule barrière avec une adresse mémoire codée en dur (`0xF0000000`).
* **MQTT Simple :** S'abonne au topic global `parking/barrier`.
* **Commandes Basiques :** Accepte uniquement les payloads `OPEN` et `CLOSE`.
* **Séquence Fixe :** Utilise des tableaux statiques `seq_open` et `seq_close` pour la rotation du moteur.
* **Sécurité :** Vérifie l'état actuel (`is_open`) avant d'agir pour éviter d'ouvrir une barrière déjà ouverte.

---

## v1 : Gestion des IDs et du Sens (Logiciel)
*Fichier source : `v1-ids-sens.c`*

Cette version introduit la flexibilité logicielle pour gérer plusieurs barrières virtuelles et différents montages physiques.

* **Identifiant en Argument :** Le programme prend un ID en paramètre (`./v1 0`, `./v1 1`...) pour personnaliser les topics MQTT.
* **Topics Dynamiques :** Les topics deviennent `parking/barrier_{ID}/state` et `parking/barrier_{ID}/sens`.
* **Inversion de Sens :** Ajout de la variable `invert_sens` et du topic `/sens`. Permet de changer le sens de rotation (Normal/Inversé) logiciellement sans re-câbler le moteur (utile selon que le moteur est monté à gauche ou à droite de la barrière).
* **Limitation :** L'adresse mémoire reste codée en dur (`0xF0000000`), donc tous les IDs pilotent physiquement le même connecteur.

---

## v2 : Mode Calibration & Test
*Fichier source : `v2-configuration.c`*

Outil de diagnostic conçu pour déterminer le calibrage exact du moteur.

* **Topic de Test :** Écoute sur `parking/test` pour ne pas interférer avec la production.
* **Contrôle Brut :** Ne gère pas d'état "Ouvert/Fermé". On envoie directement le nombre de pas et la direction.
* **Commandes Spécifiques :**
    * `pXXX` (ex: `p64`) : Lance XXX cycles en sens **P**ositif.
    * `mXXX` (ex: `m128`) : Lance XXX cycles en sens **M**inus (Inverse).
* **Objectif :** A servi à définir la constante `CYCLES_REQUIRED` (fixée à 128 par la suite pour une rortation de 90 deg).

---

## v3 : Support Multi-Adresses (Matériel)
*Fichier source : `v3-multiple-adress.c`*

Première version capable de piloter physiquement des barrières différentes sur la carte FPGA.

* **Table de Mapping :** Introduction du tableau `BARRIER_ADDRS[]` qui associe chaque ID (0, 1, 2, 3) à son adresse physique réelle (0xF0000000, 0xF0000800, etc.).
* **Sélection Dynamique :** L'argument ID (`argv[1]`) sert maintenant à choisir la bonne adresse mémoire lors de l'initialisation (`mmap`).
* **Logique Complète :** Intègre toutes les avancées précédentes (Open/Close + Inversion de sens).
* **Architecture :** Prévu pour lancer une instance du programme par barrière (ex: un processus pour la barrière 0, un autre pour la 1).

---

## v4 : Architecture Unifiée & Configuration Avancée (Finale)
*Fichier source : `v4-run-multiple.c`*

Cette version représente l'aboutissement du projet. Elle abandonne l'approche "un programme par barrière" pour un gestionnaire unique et intelligent capable de tout piloter.

* **Processus Unique :** Un seul programme (`./v4`) gère simultanément plusieurs barrières physiques. Cela réduit la charge CPU et simplifie le déploiement.
* **Structure Objet :** Le code utilise une structure C (`struct Barrier`) pour stocker isolément l'état, l'adresse mémoire et le sens de chaque moteur.
* **Configuration Dynamique (CLI) :** Les barrières à activer sont passées en arguments au lancement. Le programme ne mappe en mémoire et ne s'abonne MQTT que pour les IDs demandés.
* **Syntaxe `ID:SENS` :** Introduction d'une syntaxe pour définir l'état initial physique sans attendre de commande MQTT.
    * *Exemple :* `./v4 0:1 2:0` lance la barrière 0 en mode *Inversé* et la barrière 2 en mode *Normal*.
* **Optimisation :** Une seule connexion MQTT (Mosquitto) est partagée pour recevoir les ordres de toutes les barrières, avec un dispatching intelligent vers la bonne structure en fonction du topic reçu.

---
