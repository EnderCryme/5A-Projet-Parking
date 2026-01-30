# **Battery Management System (BMS)**

![Status](https://img.shields.io/badge/Status-Prototype-yellow)
![ECAD](https://img.shields.io/badge/ECAD-KiCad%207-blue)
![PD](https://img.shields.io/badge/USB--C-Power%20Delivery%20100W-orange)
![System](https://img.shields.io/badge/System-4S3P%20Li--Ion-green)

Ce dossier contient l’ensemble des fichiers de conception de la **carte BMS** (Battery Management System).  
L'objectif est de fournir une alimentation autonome, robuste et sécurisée pour le système embarqué hétérogène (BeagleY-AI, STM32, FPGA Nexys et moteurs).

Tout est conçu sous **KiCad 7**, avec une attention particulière aux contraintes haute tension (16.8V), aux courants forts et à la sécurité thermique.

---

# 📁 Structure du Répertoire

```
/bms
 ├── BMS_schem.kicad_sch    # Schématique complet
 ├── BMS_pcb.kicad_pcb      # Routage (4 couches, impédance contrôlée)
 ├── README.md              # Ce document
 └── calculations/          # Justifications techniques
        ├── pack_4S3P_energy.xlsx
        └── load_estimation.xlsx
```

---

## **1. Architecture Système**

Le BMS ne se contente pas de charger des batteries ; il gère toute la distribution de puissance. L'architecture repose sur un trio de composants **Texas Instruments** pour la partie puissance/sécurité, et un **RP2350** pour l'intelligence applicative.

![Architecture Simplifiée](https://upload.wikimedia.org/wikipedia/commons/thumb/3/3c/Battery_management_system_diagram.png/640px-Battery_management_system_diagram.png)

### **Le Trio de Puissance (TI)**
La mesure critique et la sécurité sont **100% hardware**, découplées du microcontrôleur pour une fiabilité maximale.

| Composant | Fonction | Pourquoi ce choix ? |
|:----------|:---------|:--------------------|
| **BQ25713** | Chargeur Buck-Boost NVDC | Gère l'USB-C PD (5V→20V) et charge le pack quelle que soit l'entrée. |
| **BQ40Z50** | Fuel Gauge & Protection | Algorithme *Impedance Track™*, balancing cellules, protections primaires. |
| **BQ296102** | Protection Secondaire | Fusible électronique ultime (OVP/UVP) totalement indépendant. |

> **Note importante :** La configuration bas niveau du BQ40Z50 (profils batterie `.gg`, calibration) nécessite l'outil **TI EV2400**. Sans cela, la puce reste en mode défaut.

---

## **2. Dimensionnement du Pack Batterie (4S3P)**

Nous avons opté pour une configuration **4S3P** (4 Série, 3 Parallèle) utilisant des cellules **Samsung INR18650‑35E** (3.7V, 3400 mAh).

### **Pourquoi 4S (14.8V - 16.8V) ?**
Lors des tests mécaniques, les moteurs pas-à-pas montraient des signes de faiblesse (à-coups, couple instable) sous 12V.
*   **Solution :** Passer à une tension pack plus élevée.
*   Le pack 4S permet d'atteindre **16.8V** en pleine charge.
*   Couplé au **Boost du BQ25713**, nous pouvons fournir un rail **20V stable** aux moteurs, garantissant couple et fluidité.

### **Capacité et Énergie**
*   **Capacité :** $3 \times 3.4\,Ah = 10.2\,Ah$
*   **Énergie :** $14.8\,V \times 10.2\,Ah \approx 151\,Wh$
*   **Tension de coupure (Sécurité) :** $3.2\,V \times 4 = 12.8\,V$

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

C'est noté. Voici la section complète **5. Bilan de Puissance & Autonomie** qui intègre les **deux tableaux** : le détail de la consommation par composant (pour justifier le dimensionnement) et le récapitulatif de l'autonomie selon les scénarios d'usage (incluant le mode Repos à 18 W).

---

## **5. Bilan de Puissance & Autonomie**

Le dimensionnement énergétique repose sur un pack **4S3P de 151 Wh** (14.8V / 10.2Ah).

### **5.1. Détail des charges connectées**
Le tableau suivant détaille la consommation maximale théorique de chaque sous-système connecté au BMS.

| Charge | Tension | Courant | Puissance |
|:-------|:--------|:--------|:----------|
| **BeagleY‑AI** | 5 V | 3 A | **15 W** |
| **Nexys A7‑100T (FPGA)** | 5 V | 3 A | **15 W** |
| **Moteurs NEMA (20 V)** | 20 V | 1 A | **20 W** |
| **Strip LED** | 12 V | 0.5 A | **6 W** |
| **2× STM32F746** | 5 V | 1 A | **5 W** |
| **2× Mini‑Stepper** | 5 V | 0.8 A | **4 W** |
| **TOTAL (Nominal)** | | | **65 W** |

> **Note :** Une marge de sécurité de **20 %** est appliquée au total nominal pour absorber les transitoires moteurs et le vieillissement des cellules, portant le dimensionnement "Pire Cas" à **78 W**.

### **5.2. Scénarios d'autonomie**
Nous avons mesuré une consommation plancher de **18 W** lorsque tout le système est connecté mais au repos (Idle). Voici les autonomies estimées :

| Scénario | Condition | Puissance | Autonomie estimée |
|:---------|:----------|:----------|:------------------|
| **Intensif (Marge)** | Full Load + 20% sécurité (pics) | 78 W | **≈ 1h 55** |
| **Intensif (Nominal)** | Tous systèmes actifs à 100% | 65 W | **≈ 2h 20** |
| **Mixte** | Usage standard moyen | 40 W | **≈ 3h 45** |
| **Repos (Idle)** | Tout connecté, pas de mouvement, CPU idle | **18 W** | **≈ 8h 20** |

> **Conclusion :** L'autonomie en mode "Repos" assure une journée complète de travail (**> 8h**) sans recharge si le système ne sollicite pas les moteurs en continu.

---
## **6. Sécurité (Safety Layers)**

La sécurité est implémentée en couches successives ("Oignon de sécurité") :

1.  **Gestionnaire (Gauge) :** Le BQ40Z50 surveille en permanence T°, V, I. Il coupe les MOSFETs en cas d'anomalie.
2.  **Protection Secondaire :** Le BQ296102 surveille uniquement les surtensions (OVP) et sous-tensions (UVP). S'il déclenche, il grille un fusible chimique commandé (CIP) pour isoler physiquement le pack.
3.  **Thermique :** 4 sondes NTC sont collées directement sur les cellules pour détecter tout emballement thermique.
4.  **Physique :** Fusibles sur les I/O et diodes TVS sur les ports externes (USB-C, borniers).
