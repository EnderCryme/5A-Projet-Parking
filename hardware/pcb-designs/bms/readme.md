# **Battery Management System (BMS)**

<img src="https://img.shields.io/badge/Status-Prototype-yellow" alt="Status" />
<img src="https://img.shields.io/badge/ECAD-KiCad%207-blue" alt="ECAD" />
<img src="https://img.shields.io/badge/USB--C-Power%20Delivery%20100W-orange" alt="PD" />
<img src="https://img.shields.io/badge/System-Battery%20Management%20System-green" alt="BMS" />

Ce dossier contient l’ensemble des fichiers associés à la **carte BMS** :
- Schéma électrique  
- Routage PCB  
- Notes de calcul (puissance, courant, autonomie)  
- Architecture de charge USB‑C PD  
- Monitoring & protection Li‑Ion

Tous les fichiers sont réalisés sous **KiCad 7**, en respectant :
- les contraintes haute tension (16.8 V max),
- les largeurs de piste adaptées aux pointes de courant,
- la sécurité électrique (OVP/UVP, pack balancing),
- la compatibilité **USB‑C Power Delivery jusqu’à 100 W**.

---

# **1. Présentation du système BMS**

Le BMS gère l’ensemble de la **chaîne d'alimentation et de protection du pack batterie**, permettant un fonctionnement autonome basé sur un pack **Li‑ion 4S3P** rechargeable via un port **USB‑C Power Delivery**.

L’architecture repose sur trois composants Texas Instruments :

| Composant | Rôle |
|----------|------|
| **BQ25713** | Chargeur buck‑boost USB‑C PD (jusqu’à 100 W) |
| **BQ296102** | Protection HV secondaire (OVP/UVP) |
| **BQ40Z50** | Gauge + Balancing + Impedance Track + SHA‑1 |

![Schéma](/hardware/pcb-designs/bms/BMS_schem.png)

---

## **Basé sur les cartes d’évaluation TI**

La conception du BMS s’appuie directement sur les meilleures pratiques et recommandations TI :

- **BQ25713EVM‑017**
- **BQ40Z50EVM‑561** ( avec **BQ296102**)

Objectifs :
- stabilité optimale du chargeur,  
- sécurité conforme aux standards TI,  
- compatibilité totale avec l’écosystème TI Fuel Gauge.

---

## **Programmation et configuration — TI EV2400 requise**

L'initialisation complète nécessite :

### **TI EV2400 USB Interface Adapter**

Il permet :
- communication SMBus/I2C/HDQ,
- configuration du BQ40Z50,
- chargement des profils batterie (.gg),
- utilisation de GaugeStudio, bqStudio et Impedance Track.

**Sans EV2400, le BQ40Z50 ne peut pas être configuré correctement.**

---

# **2. Pourquoi l’USB Type‑C Power Delivery ?**

### ✔ Compatible avec les chargeurs modernes  
Tensions gérées : **5 V → 20 V**.

### ✔ Négociation automatique des profils PD  
Le BQ25713 gère : **5 / 9 / 12 / 15 / 20 V**.

### ✔ Sécurisé et efficace  
La puissance absorbée = puissance négociée.

### ✔ Très flexible  
Jusqu’à **100 W**, utilisation universelle.

---

# **3. Dimensionnement du Battery Pack – 4S3P**

Cellules : **Samsung INR18650‑35E** (3.7 V, 3400 mAh).

### **Architecture**
- **4S** → tension ×4  
- **3P** → capacité ×3

### **Tensions par cellule**
- Max charge : **4.20 V**
- Nominale : **3.7 V**
- **Min sécurité : 3.20 V** (valeur retenue)
- Zone d’usure : < 2.75 V
- Zone dangereuse : < 2.50 V

### **Tension pack 4S**
- Nominale : **14.8 V**
- Max : **16.8 V**
- **Plancher sécurité : 3.2 V × 4 = 12.8 V**

### **Capacité totale**
3 × 3.4 Ah = **10.2 Ah**

### **Énergie**
14.8 V × 10.2 Ah = **151 Wh**

---

# **3.1. Pourquoi un pack 4S3P ?**

### ✔ Alignement initial avec la tension système  
Le système fonctionne entre **12 V et 15 V** :

- DC/DC vers 5 V (BeagleY‑AI, STM32, Nexys)
- Accessoires en 12 V

Un pack 4S donne :
- 14.8 V nominal
- 16.8 V max
- **≥ 12.8 V (tension plancher sécurité)**

→ Idéal pour limiter les conversions énergivores.

---

## ✔ Pourquoi une tension plus élevée a été nécessaire pour les moteurs ?

Tests mécaniques → les moteurs pas‑à‑pas présentaient :
- à‑coups à haute vitesse,
- courant dynamique insuffisant,
- couple instable en accélération.

👉 Les moteurs sont beaucoup plus réguliers sous **18–20 V**.

### Une tension plus haute permet :
- meilleur contrôle du courant dans les bobines,
- montée en vitesse plus rapide,
- réduction drastique des à‑coups.

---

## ✔ Pourquoi rester en 4S alors ?

Le pack 4S (16.8 V max) + le **buck‑boost BQ25713** permet de :
- **booster à 20 V pour les moteurs**,  
- bucker pour les rails 12 V, 5 V, 3.3 V.

Avantages :
- pack compact,
- évite un passage en 5S,
- reste compatible USB‑C PD (max 20 V),
- efficacité optimisée.

---

# **4. Calcul de la consommation**

| Charge | Tension | Courant | Puissance |
|--------|----------|-----------|-----------|
| 2× STM32F746 | 5 V | 0.5 A | **5 W** |
| BeagleY‑AI | 5 V | 3 A | **15 W** |
| Nexys A7‑100T | 5 V | 3 A | **15 W** |
| Strip LED | 12 V | 0.5 A | **6 W** |
| NEMA (20 V) | 20 V | 1 A | **20 W** |
| 2× Mini‑Stepper | 5 V | 0.4 A | **4 W** |

Total nominal = **65 W**

---

# **4.1. Marge de sécurité 20 %**

Utilisée pour absorber :
- transitoires moteurs,
- pics BeagleY‑AI,
- pertes DC/DC,
- dérive thermique,
- vieillissement cellules.

### P_total = 65 W × 1.20 = **78 W**

Compatible avec la limite **100 W USB‑C PD**.

---

# **5. Autonomie**

### Sans marge (65 W)
→ 151 Wh / 65 W = **≈ 2.3 h**

### Avec marge (78 W)
→ 151 Wh / 78 W = **≈ 2 h**

---

## **5.1. Tableau récapitulatif**

| Scénario | Puissance | Autonomie |
|----------|-----------|-----------|
| Charge max (sans marge) | 65 W | **≈ 2.3 h** |
| Charge max (marge 20 %) | 78 W | **≈ 2.0 h** |
| Usage typique | 40 W | **≈ 3.7 h** |
| Usage réduit | 25 W | **≈ 6 h** |

---

# **6. Structure du dossier**

```
/bms
 ├── BMS_schem.kicad_sch
 ├── BMS_pcb.kicad_pcb
 ├── README.md
 └── calculations/
        ├── pack_4S3P_energy.xlsx
        └── load_estimation.xlsx
```
