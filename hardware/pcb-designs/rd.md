# **PCB Design**

## **1. BMS – Battery Management System**

Dans le cadre du projet, il m’a été confié de gérer **l’ensemble de la partie puissance**, ainsi que d’anticiper différents **scénarios hors‑réseau**, impliquant l’intégration d’un système de batteries rechargeable.

![BMS](/hardware/pcb-designs/bms/BMS_schem.png)

L’alimentation principale se fait via un port **USB Type‑C avec Power Delivery (PD)** pour plusieurs raisons déterminantes :

### **Pourquoi l’USB Type‑C PD ?**
- **Standard universel** : compatible avec la majorité des chargeurs modernes.  
- **Négociation automatique de puissance (PD)** :  
  Le système peut demander exactement la puissance dont il a besoin, et un appareil connecté à notre BMS ne tirera que ce qu’il est autorisé à consommer.  
- **Flexibilité du système** :  
  Cette approche permet d’adapter le nombre de cellules dans la batterie, mais aussi le type de chargeur utilisé, avec une plage très large de puissance :  
  **min. 5 W → max. 100 W**.  

L’ensemble du système s’adapte donc automatiquement au chargeur disponible (5V/9V/12V/15V/20V selon les PDO), offrant une robustesse optimale pour des scénarios variés : installations autonomes, postes IoT isolés, prototypes portables, alimentation redondante, etc.

---

## **2. Capteur de lumière**

L’intégration d’un **capteur de luminosité** permet de détecter un seuil d’illumination et d’activer automatiquement l’éclairage.

### Objectif
- Allumer les LED dès qu’il fait suffisamment sombre (ex : crépuscule).  
- Éviter d’éclairer inutilement en pleine journée.  

### Couplage avec un capteur de présence
Lorsqu’il est associé à un détecteur de mouvement, le système permet :
- Une **réduction de la consommation électrique** liée à l’éclairage du parking.  
- Une **diminution de la pollution lumineuse** pour les habitations environnantes.  
- Une **optimisation énergétique** du site en n’éclairant que lorsque c’est nécessaire.

---

## **3. Adaptateur MIPI/CSI 24‑pin vers 22‑pin**

Cette carte d’adaptation a pour but de rendre compatible une caméra industrielle **Sony [IMX415](https://www.aliexpress.com/p/tesla-landing/index.html?scenario=c_ppc_item_bridge&productId=1005006459824998&_immersiveMode=true&withMainCard=true&src=google-language&aff_platform=true&isdl=y&src=google&albch=shopping&acnt=248-630-5778&isdl=y&slnk=&plac=&mtctp=&albbt=Google_7_shopping&aff_platform=google&aff_short_key=UneMJZVf&gclsrc=aw.ds&&albagn=888888&&ds_e_adid=&ds_e_matchtype=&ds_e_device=c&ds_e_network=x&ds_e_product_group_id=&ds_e_product_id=en1005006459824998&ds_e_product_merchant_id=5322433151&ds_e_product_country=ZZ&ds_e_product_language=en&ds_e_product_channel=online&ds_e_product_store_id=&ds_url_v=2&albcp=23109390367&albag=&isSmbAutoCall=false&needSmbHouyi=false&gad_source=1&gad_campaignid=23099403303&gbraid=0AAAAACWaBwcpBX66pViW9Q9uEVkNLbb5u&gclid=Cj0KCQiAp-zLBhDkARIsABcYc6s10qr6-Mvkb30nFB_ocI8gzYVvJoYXCnLD3EiTIj9k3wjnMAxINmsaAiD-EALw_wcB)** (connecteur **24‑pins**) avec notre matériel basé sur **BeagleBone AI‑64 / BeagleBone Y‑AI**, dont le port CSI exploite un connecteur **22‑pins**.

### Pourquoi un adaptateur ?
- Les caméras industrielles (dont l’IMX415) utilisent souvent un **pinout propriétaire 24‑pins**.  
- La plateforme BBY nécessite un **pinout standardisé 22‑pins CSI‑2**.  
- Les signaux MIPI doivent être réaffectés proprement (Clock lanes, Data lanes, I²C, alimentation).  

### Rôle de la carte
- Conversion **mécanique** : adaptation du connecteur.  
- Conversion **électrique passive** : réaffectation des signaux MIPI CSI‑2 à la bonne numérotation.  
- Maintien de l’intégrité du signal haute‑vitesse (impédance contrôlée, longueur équilibrée, minimisation des paires différentielles).

Cela permet d’utiliser une caméra haute résolution avec notre plateforme BBY sans recourir à un module propriétaire.
