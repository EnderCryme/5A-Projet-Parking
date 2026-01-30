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

La conception du BMS s’appuie directement sur les meilleures pratiques et les topologies recommandées par Texas Instruments, en particulier :

- **BQ25713EVM‑017**  
- **BQ40Z50EVM‑561**  
- **BQ2961x evaluation modules**  

Le schéma, le layout, et la sélection des composants critiques (drivers, MOSFETs, filtres, composants sensing) suivent les recommandations issues de ces EVM afin d’assurer :

- une stabilité optimale du chargeur,  
- une sécurité conforme aux standards TI,  
- une compatibilité totale avec l’écosystème TI Fuel Gauge.

---

## **Programmation et configuration — TI EV2400 requise**

Pour configurer correctement les composants TI (en particulier le **BQ40Z50**), il est nécessaire d’utiliser :

### **TI EV2400 USB Interface Adapter**

Ce programmateur permet :  
- la communication SMBus/I2C/HDQ avec le BMS,  
- le flashage et la configuration des profils batterie (.gg files),  
- l’accès aux outils officiels TI :  
  - **GaugeStudio**,  
  - **Battery Management Studio (bqStudio)**,  
  - **Data Memory editor**,  
  - **Impedance Track learning cycle tools**.

**Sans l’EV2400, il est impossible d’initialiser correctement le fuel gauge BQ40Z50.**

---

# **2. Pourquoi l’USB Type‑C Power Delivery ?**

### Compatible avec la majorité des chargeurs modernes de PC  
Tensions supportées : **5 V → 20 V**.

### Négociation automatique (PDO contracts)  
Le BQ25713 sélectionne automatiquement :  **5 V / 9 V / 12 V / 15 V / 20 V**

### Sécurisé et efficace  
La puissance absorbée est limitée au profil négocié PD.

### ✔ Extrêmement flexible  
Adaptable à tous les scénarios off‑grid et chargeurs jusqu’à **100 W**.

---
# **3. Dimensionnement du Battery Pack – 4S3P**

Cellules utilisées : **Samsung INR18650‑35E** (3.7 V, 3400 mAh).

### **Architecture**
- **4S** → tension ×4  
- **3P** → capacité ×3  

### **Tension**
- Nominale : **14.8 V**  
- Max charge : **16.8 V**

### **Capacité totale**
3 × 3.4 Ah = **10.2 Ah**

### **Énergie**
14.8 V × 10.2 Ah = **151 Wh**

# **3.1. Pourquoi un pack 4S3P ?**

Le choix du pack **4S3P** n’est pas arbitraire : il découle directement des besoins en tension et en dynamique du système.

## **✔ Alignement initial avec la tension maximale du système**
Le cœur du système électronique fonctionne principalement autour de **12 V à 15 V**, après régulation :

- Les DC/DC convertissent vers 5 V pour la BeagleY‑AI, les STM32 et la Nexys.  
- Les accessoires (LEDs, drivers logiques…) utilisent aussi 12 V.  

Un pack **4S Li‑Ion** présente :

- Tension nominale : **14.8 V**  
- Tension max : **16.8 V**  
- Tension min : **12 V** (à décharge presque complète)

👉 **4S couvre parfaitement la plage 12–15 V**, sans multiplier les conversions DC/DC,  
ni gaspiller d’énergie.

---

## **✔ Pourquoi une tension plus élevée a été nécessaire pour les moteurs ?**

Lors des tests mécaniques, on a constaté que :

- Les **moteurs pas‑à‑pas** (surtout le NEMA) généraient  
  des **à‑coups** à vitesse élevée.  
- Ces à‑coups devenaient très visibles lors des accélérations rapides  
  et des micro‑steps.  
- Les drivers steppers limitaient le courant, mais pas assez vite pour lisser l'effort mécanique.

Après analyse, la cause était claire :

### **Les moteurs nécessitaient une tension plus élevée pour assurer :**
- un courant dynamique suffisant,  
- une montée en vitesse plus rapide,
- un meilleur couple dans les accélérations,
- et donc **moins d’à‑coups mécaniques**.

Plus la tension est haute, plus le driver peut **forcer l'évolution du courant dans les bobines**,  
ce qui améliore considérablement la qualité du mouvement.

Lors de l’expérimentation, les moteurs devenaient nettement plus stables autour de **18–20 V**.

---

## **✔ Pourquoi on reste en 4S alors ?**

Parce que **4S fournit déjà 16.8 V max**, et, avec le BQ25713 **buck‑boost**, le système peut :  

- booster vers **20 V** pour les moteurs,  
- ou bucker pour les autres rails (12 V, 5 V, 3.3 V).

Cela permet de :

- garder un pack compact,  
- éviter un passage en 5S (overkill et incompatible avec beaucoup de chargeurs),  
- rester compatible USB‑C PD (max 20 V),  
- minimiser les pertes globales du système.

---
# **4. Calcul de la consommation**

À partir des modules du système :

| Charge | Tension | Courant | Puissance |
|-------|---------|----------|-----------|
| 2× STM32F746 | 5 V | 0.5 A | **5 W** |
| BeagleY‑AI | 5 V | 3 A | **15 W** |
| Nexys A7‑100T | 5 V | 3 A | **15 W** |
| Strip LED | 12 V | 0.5 A | **6 W** |
| NEMA (20 V) | 20 V | 1 A | **20 W** |
| 2× Mini‑Stepper | 5 V | 0.4 A | **4 W** |

### **Puissance totale (Pₜₒₜ nominale)**  
Pₜₒₜ = 5 + 15 + 15 + 6 + 20 + 4  
Pₜₒₜ = **65 W**

---

# **4.1. Ajout d’une marge de sécurité de 20 %**

Pour dimensionner correctement le BMS, le DC/DC, les pistes, les MOSFETs et les protections,  
nous ajoutons une **marge de puissance de 20 %**, afin d’absorber :

- transitoires de courant moteurs → stepper / NEMA  
- pics d’appel sur la BeagleY‑AI  
- variabilité de rendement DC/DC  
- dérive thermique  
- vieillissement des cellules  

### **Pₜₒₜ avec marge = Pₙₒₘ × 1.20**

65 W × 1.20 = **78 W**

➡ Le BMS est donc calibré pour **≈ 80 W réels**, parfaitement compatible avec  
la limite **100 W du chargeur USB‑C Power Delivery**.

---

# **5. Autonomie (avec et sans marge)**

### **Sans marge (puissance nominale = 65 W)**  
151 Wh / 65 W = **≈ 2.3 h**

### **Avec marge (puissance effective = 78 W)**  
151 Wh / 78 W = **≈ 1.94 h ≈ 2 h**

---

# **5.1. Tableau récapitulatif autonomie**

| Scénario | Puissance | Autonomie |
|----------|-----------|-----------|
| Charge maximale (sans marge) | 65 W | **≈ 2.3 h** |
| Charge maximale (avec 20 % marge) | 78 W | **≈ 2.0 h** |
| Usage typique (~40 W) | 40 W | **≈ 3.7 h** |
| Usage réduit (~25 W) | 25 W | **≈ 6 h** |

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
