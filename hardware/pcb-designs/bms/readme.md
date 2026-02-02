# **Battery Management System (BMS)**

![Status](https://img.shields.io/badge/Status-Prototype-yellow)
![ECAD](https://img.shields.io/badge/ECAD-KiCad%207-blue)
![PD](https://img.shields.io/badge/USB--C-Power%20Delivery%20100W-orange)
![System](https://img.shields.io/badge/System-4S3P%20Li--Ion-green)

Ce dossier contient l’ensemble des fichiers de conception de la **carte BMS** (Battery Management System).  
L'objectif est de fournir une alimentation autonome, robuste et sécurisée pour le système embarqué hétérogène (BeagleY-AI, STM32, FPGA Nexys et moteurs).

Tout est conçu sous **KiCad 7**, avec une attention particulière aux contraintes haute tension (16.8 V), aux courants forts et à la sécurité thermique.

---

# 📁 Structure du Répertoire

```
bms/                               # Layout et ressources de design du BMS
   ├── calculations/               # Justifications techniques
   │   ├── load_estimation.csv
   │   └── pack_4S3P_energy.csv
   ├── designs/                    # Sources du projet KiCad
   │   ├── BMS.csv                 # BOM compatible JLCPCB
   │   ├── BMS_schem.kicad_prl     # Fichier projet KiCad du BMS
   │   ├── BMS_schem.kicad_sch     # Schématique complet
   │   ├── BMS_pcb.kicad_pcb       # Routage (4 couches, impédance contrôlée)
   │   ├── BMS.pdf                 # Feuilles circuits au format pdf ⚠ Ne pas imprimer comme tel,
   │   └── ....                      il y'a des feuilles inutiles utilisés pour simplifié le circuitage
   ├── references/                 # Datasheets composants (STM32, STUSB...)
   ├── test-EVM/                   # Tests sur carte d'évaluation (BQ40Z50)
   ├── BMS_schem.png
   ├── bilan-puissance-max.png
   ├── readme.md
   └── .... ⚠ le firmware RP2350 est trouvable au : /software/sw-fw-BMS
```

---

## **1. Architecture Système**

Le BMS ne se contente pas de charger des batteries ; il gère toute la distribution de puissance. L'architecture repose sur un trio de composants **Texas Instruments** pour la partie puissance/sécurité, et un **RP2350** pour l'intelligence applicative.

![Architecture Simplifiée](BMS_schem.png)

### **Le Trio de Puissance (TI)**
La mesure critique et la sécurité sont **100 % hardware**, découplées du microcontrôleur pour une fiabilité maximale.

| Composant | Fonction | Pourquoi ce choix ? |
|:----------|:---------|:--------------------|
| **BQ25713** | Chargeur Buck-Boost NVDC | Gère l'USB-C PD (5V→20V) et charge le pack quelle que soit l'entrée. |
| **BQ40Z50** | Fuel Gauge & Protection | Algorithme *Impedance Track™*, balancing cellules, protections primaires. |
| **BQ296102** | Protection Secondaire | Fusible électronique ultime (OVP/UVP) totalement indépendant. |

> **Note importante :** La configuration bas niveau du BQ40Z50 (profils batterie `.gg`, calibration) nécessite l'outil **TI EV2400**. Sans cela, la puce reste en mode défaut.

---

## **2. Dimensionnement du Battery Pack – 4S3P**

Le choix des cellules s'est porté sur des **Samsung INR18650‑35E** (3.7 V, 3400 mAh), assemblées en une configuration **4S3P**.

### **Caractéristiques du Pack**
*   **Capacité :** $3 \times 3.4\,Ah = 10.2\,Ah$
*   **Énergie :** $14.8\,V \times 10.2\,Ah = 151\,Wh$
*   **Tension Nominale :** 14.8 V
*   **Tension Max (Charge) :** 16.8 V
*   **Tension Min (Sécurité) :** 12.8 V

### **2.1. Justification du 4S et Évolution vers 20 V**

**L'approche initiale :**
Le pack 4S a été dimensionné initialement pour s'aligner sur une tension système globale de **12 V à 15 V**, idéale pour limiter les pertes de conversion vers les rails logiques (5V) et périphériques standards (12V).

**Le constat mécanique :**
Lors des tests d'intégration, nous avons remarqué que le moteur pas-à-pas de l'ascenseur (Stepper) manquait de fluidité sous 15 V (à-coups à haute vitesse, couple instable). Les essais ont montré un comportement mécanique optimal et parfaitement fluide sous **18–20 V**.

**La solution architecturale (Buck-Boost) :**
Ce changement de prérequis n'a pas impacté la batterie. L'architecture de puissance de la carte BMS intègre une topologie flexible :
*   **Buck (Abaisseur) :** Pour générer les rails 12 V, 5 V et 3.3 V avec un haut rendement.
*   **Boost (Élévateur) :** Pour rehausser la tension batterie (12.8V - 16.8V) vers le rail **20 V** nécessaire aux moteurs.

> Cette flexibilité permet de conserver un pack compact (4S) et compatible USB-C PD, tout en fournissant la haute tension requise par la mécanique.
---

## **3. Entrée USB-C Power Delivery**

L'alimentation se fait via un port USB-C compatible **Power Delivery (PD) jusqu'à 100W**.

*   **Universel :** Fonctionne avec n'importe quel chargeur de laptop ou téléphone (5V, 9V, 12V, 15V, 20V).
*   **Négociation Automatique :** Le BQ25713 négocie la tension max disponible et adapte son étage Buck-Boost pour charger le pack 4S (qui demande ~16.8V).
*   **Rendement :** L'architecture NVDC (Narrow Voltage DC) optimise l'efficacité et permet au système de démarrer même si la batterie est vide.

---

## **4. Intelligence & Supervision : RP2350 vs STM32**

Pour l'interface utilisateur (OLED), la télémétrie et la supervision non-critique, nous avons choisi le **RP2350**.

### **Pourquoi pas un STM32 standard (ex: F4/G4) ?**
Nous avons appliqué un **Indice de Performance Normalisé (IPN)** pour objectiver le choix :

$$ IPN = \frac{\text{Cœurs} \times \text{Fréquence} \times \text{GPIO}}{\text{Prix (€)}} $$

*   **STM32 (G4 typique) :** 1 cœur, 170MHz, cher (~4.50€) $\rightarrow$ **IPN ≈ 444**
*   **RP2350 :** 2 cœurs, 150MHz, beaucoup de GPIO, pas cher (~1.20€) $\rightarrow$ **IPN ≈ 8500**

Le RP2350 est **~19x plus rentable** pour ce rôle de supervision. Il récupère les infos du BQ40Z50 via SMBus et gère l'affichage, laissant la sécurité pure aux puces TI.

---

## **5. Bilan de Puissance & Autonomie**

Le dimensionnement énergétique du BMS est dicté par une architecture matérielle complexe et hétérogène. L'image ci-dessous résume l'ensemble des composants actifs dans le scénario de consommation maximale ("Max du Max").

![Hardware Ecosystem](bilan-puissance-max.png)
*Vue d'ensemble des charges connectées : FPGA, Processeurs AI, Microcontrôleurs et Actionneurs.*

### **5.1. Détail de la consommation (Worst Case)**
Le tableau suivant quantifie la puissance requise lorsque tous les éléments ci-dessus sont sollicités simultanément (Calcul intensif + Moteurs en couple de maintien ou mouvement).

| Charge | Tension | Courant Max | Puissance |
|:-------|:--------|:------------|:----------|
| **BeagleY‑AI** | 5 V | 3 A | **15 W** |
| **Nexys A7‑100T (FPGA)** | 5 V | 3 A | **15 W** |
| **Moteurs NEMA (via Boost)** | 20 V | 1 A | **20 W** |
| **Strip LED** | 12 V | 0.5 A | **6 W** |
| **2× STM32F746** | 5 V | 1 A | **5 W** |
| **2× Mini‑Stepper** | 5 V | 0.8 A | **4 W** |
| **TOTAL (Nominal)** | | | **65 W** |

> **Dimensionnement Sécuritaire :** Avec une marge de sécurité de **20 %** (pics de courant moteurs et rendement des convertisseurs), le système est dimensionné pour fournir jusqu'à **78 W** en pointe.

### **5.2. Scénarios d'autonomie**
Le pack batterie **4S3P (151 Wh)** offre une grande flexibilité d'usage. Nous avons mesuré une consommation plancher (Idle) de **18 W** lorsque tout le système est alimenté mais en attente d'instruction.

| Scénario | Condition | Puissance | Autonomie estimée |
|:---------|:----------|:----------|:------------------|
| **Intensif (Marge)** | Full Load + 20 % (Stress test) | 78 W | **≈ 1h 55** |
| **Intensif (Nominal)** | Robot en mouvement + IA active | 65 W | **≈ 2h 20** |
| **Mixte** | Usage standard moyen | 40 W | **≈ 3h 45** |
| **Repos (Idle)** | Tout connecté, moteurs à l'arrêt | **18 W** | **≈ 8h 20** |

> **Conclusion :** L'architecture garantit près de **2 heures** d'autonomie en régime maximal hors réseau (calcul IA + déplacement continu) et assure une journée complète (**>8h**) en veille active, permettant la continuité du service de parking même en cas de coupure du réseau électrique, ou durant une maintenant.

### **5.3. Extension d'Autonomie (Solaire / Éolien 50 W)**

Pour répondre aux exigences d'un fonctionnement en extérieur ou en site isolé, l'architecture d'alimentation permet l'intégration de sources d'énergie renouvelables. Le dimensionnement cible un apport de **50 W** (ex: panneau solaire monocristallin standard ou petite éolienne).

Cet apport transforme le BMS en système hybride, capable de recharge en cours de fonctionnement (*Pass-through Charging*).

#### **Impact du scénario 50 W sur le bilan énergétique**
L'injection de 50 W permet de couvrir intégralement la consommation au repos et mixte, et de compenser drastiquement la consommation en pleine charge.

| Mode de fonctionnement | Consommation ($P_{load}$) | Apport Solaire ($P_{in}$) | Bilan Net sur Batterie ($P_{net}$) | Conséquence |
|:---|:---:|:---:|:---:|:---|
| **Repos (Idle)** | 18 W | + 50 W | **+ 32 W (Recharge)** | **Autonomie Infinie** + Recharge rapide du pack |
| **Mixte (Standard)** | 40 W | + 50 W | **+ 10 W (Recharge)** | **Autonomie Infinie** + Maintien de charge |
| **Intensif (Nominal)** | 65 W | + 50 W | **- 15 W (Décharge)** | Décharge très lente. Autonomie étendue à **≈ 10h** (vs 2h20) |

#### **Méthodologie de calcul du gain**
L'autonomie étendue ($T_{ext}$) est calculée en fonction du **Bilan Net** de puissance puisée sur la batterie. Avec un robot consommant **65 W** et un apport de **50 W**, le différentiel est de :

$$P_{net} = 65~W - 50~W = \mathbf{15~W}$$

L'autonomie théorique devient alors :
$$T_{ext} = \cfrac{E_{batt}}{P_{net}} = \cfrac{151~Wh}{15~W} \approx \mathbf{10,06~Heures}$$

#### **Implémentation technique simplifiée (USB-C PD)**
L'intégration de cette source d'énergie est rendue native par l'usage du port **USB-C** bidirectionnel. Il n'est pas nécessaire de modifier le hardware du BMS, ni d'ajouter des convertisseurs MPPT externes complexes.

1.  **Côté Source (Solaire/Éolien) :** Il suffit d'équiper la sortie du panneau d'un **contrôleur USB-PD standard**. Celui-ci négocie automatiquement la tension optimale (ex: 20 V) dès la connexion.
2.  **Gestion Intelligente (RP2350 & BQ25713) :**
    *   Le **RP2350** détecte la connexion et communique avec le BQ25713 via I2C.
    *   Il identifie le profil de puissance disponible (PDO) annoncé par la source.
    *   Il adapte dynamiquement la limite de courant d'entrée ($I_{in\_{lim}}$) pour maximiser la puissance extraite sans effondrer la tension du panneau, garantissant une stabilité parfaite du système hybride.

> **Conclusion "Smart Grid" :** L'apport solaire ne se contente pas de recharger la batterie ; il soulage le pack de **77 %** de l'effort en charge nominale. Cela multiplie l'autonomie opérationnelle par un facteur **4**, permettant de tenir une journée de travail intense sans jamais se brancher au secteur.

---
## **6. Sécurité (Safety Layers)**

La sécurité est implémentée en couches successives ("Oignon de sécurité") :

1.  **Gestionnaire (Gauge) :** Le BQ40Z50 surveille en permanence T°, V, I. Il coupe les MOSFETs en cas d'anomalie.
2.  **Protection Secondaire :** Le BQ296102 surveille uniquement les surtensions (OVP) et sous-tensions (UVP). S'il déclenche, il grille un fusible chimique commandé (CIP) pour isoler physiquement le pack.
3.  **Thermique :** 4 sondes NTC sont collées directement sur les cellules pour détecter tout emballement thermique.
4.  **Physique :** Fusibles sur les I/O et diodes TVS sur les ports externes (USB-C, borniers).

---

## **7. Interfaces d'Entrées/Sorties & Extensions (I/O)**

Le BMS a été conçu pour être plus qu'une simple alimentation : c'est un périphérique intelligent et interactif. L'architecture autour du **RP2350** exploite ses nombreuses broches pour offrir des fonctions de diagnostic local, de pilotage fin des sorties et de mise à jour simplifiée.

### **7.1. Port Master & Programmation (Lien BeagleBone)**
Une interface de communication privilégiée relie le BMS au cerveau du robot (BeagleBone AI-64). Ce port remplit un double rôle crucial via les lignes de données (D+/D-) :
*   **Télémétrie & Contrôle :** En fonctionnement normal, le BeagleBone récupère les statistiques (SOC, puissance instantanée) via une liaison série/USB.
*   **Mise à jour Firmware (Mode Prog) :** Le BMS peut basculer en mode "Bootloader", permettant au BeagleBone de reflasher le RP2350 à la volée. Cela garantit un système évolutif, capable de recevoir des correctifs ou de nouvelles stratégies de charge sans démontage matériel.

### **7.2. Interface Homme-Machine (IHM) Locale**
Pour faciliter le diagnostic sur le terrain (sans avoir besoin de connecter un PC), le BMS intègre sa propre interface utilisateur :
*   **Écran OLED (I2C) :** Affiche en temps réel l'état de santé du pack (SOH), le pourcentage de batterie, la tension globale et le courant consommé/chargé.
*   **Boutons de Navigation :** Une série de boutons poussoirs permet de naviguer dans les menus affichés sur l'OLED pour :
    *   Consulter les tensions individuelles des cellules.
    *   Modifier les réglages à la volée (ex : forcer un mode "Stockage" à 50% de charge).
    *   Réinitialiser les erreurs éventuelles.

### **7.3. Supervision & Pilotage des Rails de Sortie**
Le BMS ne se contente pas de fournir de la puissance, il vérifie la qualité de ce qu'il délivre et contrôle la distribution :
*   **ADC de Monitoring (Feedback) :** Le RP2350 mesure en continu via ses ADCs les tensions réelles présentes sur les sorties de puissance. Cela permet de détecter une sous-tension (brownout) ou une défaillance d'un régulateur en aval.
*   **GPIOs "Enable" :** Chaque rail de puissance majeur (notamment les 4 sorties principales) est piloté par un commutateur de charge (*Load Switch*) activable individuellement par logiciel.
    *   *Scénario :* Le BMS peut choisir de couper l'alimentation des moteurs tout en gardant l'unité de calcul (BeagleBone) allumée en cas de batterie faible critique.

### **7.4. Gestion Thermique Active & Sécurité Étendue**
Compte tenu des puissances en jeu (jusqu'à 100W en crête), la gestion thermique est renforcée :
*   **NTC Additionnelles :** Des connecteurs pour sondes de température externes permettent de surveiller des points chauds spécifiques (ex: transistors de puissance, connecteurs forts courants).
*   **Pilotage Ventilateur (PWM) :** Une sortie PWM dédiée permet de piloter un micro-ventilateur. Le RP2350 asservit la vitesse du ventilateur à la température mesurée par les NTCs, assurant un refroidissement actif de l'étage de puissance lors des charges rapides ou des fortes sollicitations moteurs.

> **Synthèse I/O :** Cette panoplie d'interfaces transforme le BMS en un véritable **superviseur d'énergie**, offrant une observabilité totale et une capacité d'action autonome pour protéger le robot.
