# **PCB Design**
![Status](https://img.shields.io/badge/Status-Prototype-yellow)
![ECAD](https://img.shields.io/badge/ECAD-KiCad%207-blue)
![PD](https://img.shields.io/badge/USB--C-Power%20Delivery%20100W-orange)
![BMS 100W](https://img.shields.io/badge/System-Battery%20Management%20System-green)

Ce répertoire contient l’ensemble des **cartes électroniques (PCB)** développées pour le système.  
Tous les schémas et routages ont été réalisés sous **KiCad 7**, en respectant les contraintes des signaux rapides (MIPI, USB), la sécurité électrique, ainsi que la compatibilité avec **USB‑C Power Delivery**.

---
# 📁 Structure du Répertoire

```
/pcb-designs
   ├── adaptateur-24pin/            # Convertisseur Mipi to CSI
   │   ├── GERBER-Adaptateur/
   │   ├── Adapat_24pin_22pin.kicad_pcb
   │   ├── Adapat_24pin_22pin.kicad_sch
   │   └── Adapat_24pin_22pin.rar
   ├── bms/                            # Layout et ressources de design du BMS
   │   ├── calculations/               # Justifications techniques
   │   │   ├── load_estimation.csv
   │   │   └── pack_4S3P_energy.csv
   │   ├── designs/                    # Sources du projet KiCad
   │   │   ├── BMS.csv                 # BOM compatible JLCPCB
   │   │   ├── BMS_schem.kicad_prl     # Fichier projet KiCad du BMS
   │   │   ├── BMS_schem.kicad_sch     # Schématique complet
   │   │   ├── BMS_pcb.kicad_pcb       # Routage (4 couches, impédance contrôlée)
   │   │   ├── BMS.pdf                 # Feuilles circuits au format pdf ⚠ Ne pas imprimer comme tel,
   │   │   └── ....                      il y'a des feuilles inutiles utilisés pour simplifié le circuitage
   │   ├── references/                 # Datasheets composants (STM32, STUSB...)
   │   ├── test-EVM/                   # Tests sur carte d'évaluation (BQ40Z50)
   │   ├── BMS_schem.png
   │   ├── bilan-puissance-max.png
   │   ├── readme.md
   │   └── .... ⚠ le firmware RP2350 est trouvable au : /software/sw-fw-BMS
   ├── common-libs/                    # Lib cstm avec les empreintes steps et schémas utilisés
   └── detection-lumiere/              # Détection d'intensité lumineuse
       ├── Gerber/
       ├── Lumiere.kicad_pcb
       ├── Lumiere.kicad_sch
       └── readme.md         
```

---

## **1. BMS – Battery Management System**

Dans le cadre du projet, il m’a été confié de gérer **toute la partie puissance**, ainsi que d’anticiper différents **scénarios hors‑réseau**, impliquant l’utilisation d’un système de batteries rechargeable.

![BMS](/hardware/pcb-designs/bms/BMS_schem.png)

L’alimentation principale repose sur un port **USB Type‑C avec Power Delivery (PD)** pour plusieurs raisons :

### **Pourquoi l’USB Type‑C PD ?**
- **Standard universel** : compatible avec la majorité des chargeurs actuels.  
- **Négociation automatique de puissance (PD)** :  
  Le système consomme précisément ce dont il a besoin, et limite ce qu’il fournit.  
- **Flexibilité du système** :  
  Permet d’adapter le nombre de cellules, l’autonomie et le chargeur utilisé.  
  Plage de puissance supportée : **5 W → 100 W**.

Le système sélectionne automatiquement la tension adéquate parmi les différents PDO du chargeur (5V / 9V / 12V / 15V / 20V).  
Cela le rend particulièrement robuste pour des scénarios variés : installations autonomes, postes IoT isolés, alimentation redondante, robotique mobile, etc.

---

## **2. Capteur de lumière**

L’intégration d’un **capteur de luminosité** permet de détecter un niveau d’éclairage insuffisant pour activer automatiquement l’éclairage du site.

### Objectif
- Allumer les LED dès qu’il fait suffisamment sombre (ex. crépuscule).  
- Éviter tout éclairage inutile en pleine journée.

### Couplage avec un capteur de présence
Associé à un détecteur de mouvement, ce capteur permet :
- Une **réduction de la consommation électrique**.  
- Une **diminution de la pollution lumineuse** pour le voisinage.  
- Une **optimisation énergétique** en n’éclairant que lorsque cela est nécessaire.

Cette approche rend le système plus intelligent, écoresponsable et parfaitement adapté à une installation extérieure automatique.

---

## **3. Adaptateur MIPI/CSI 24‑pin vers 22‑pin**

Cette carte d’adaptation permet de rendre compatible une caméra industrielle **Sony [IMX415](https://www.aliexpress.com/p/tesla-landing/index.html?scenario=c_ppc_item_bridge&productId=1005006459824998&_immersiveMode=true&withMainCard=true&src=google-language&aff_platform=true&isdl=y&src=google&albch=shopping&acnt=248-630-5778&isdl=y&slnk=&plac=&mtctp=&albbt=Google_7_shopping&aff_platform=google&aff_short_key=UneMJZVf&gclsrc=aw.ds&&albagn=888888&&ds_e_adid=&ds_e_matchtype=&ds_e_device=c&ds_e_network=x&ds_e_product_group_id=&ds_e_product_id=en1005006459824998&ds_e_product_merchant_id=5322433151&ds_e_product_country=ZZ&ds_e_product_language=en&ds_e_product_channel=online&ds_e_product_store_id=&ds_url_v=2&albcp=23109390367&albag=&isSmbAutoCall=false&needSmbHouyi=false&gad_source=1&gad_campaignid=23099403303&gbraid=0AAAAACWaBwcpBX66pViW9Q9uEVkNLbb5u&gclid=Cj0KCQiAp-zLBhDkARIsABcYc6s10qr6-Mvkb30nFB_ocI8gzYVvJoYXCnLD3EiTIj9k3wjnMAxINmsaAiD-EALw_wcB)** (connecteur **24‑pins**) avec nos plateformes **BeagleBone AI‑64 / BeagleBone Y‑AI**, qui utilisent un connecteur **22‑pins CSI‑2**.

### Pourquoi un adaptateur ?
- Les caméras industrielles IMX utilisent fréquemment un **pinout 24‑pins propriétaire**.  
- Les cartes BBY reposent sur un **pinout 22‑pins CSI‑2 standardisé**.  
- Une réaffectation correcte des signaux MIPI est nécessaire :  
  - Clock lanes  
  - Data lanes  
  - Alimentation  
  - I²C / Reset / Standby  

### Rôle de la carte
- Conversion **mécanique** entre les connecteurs 24→22.  
- Conversion **électrique passive**, sans électronique active.  
- **Maintien de l’intégrité des signaux haute‑vitesse** grâce à :  
  - une impédance contrôlée,  
  - des longueurs adaptées,  
  - un routage équilibré des paires différentielles.

Cette carte garantit une compatibilité propre et robuste avec notre matériel, tout en conservant les performances du capteur IMX415.
