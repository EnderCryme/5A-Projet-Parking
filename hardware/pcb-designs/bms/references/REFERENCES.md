# 📚 Références Techniques & Design

Ce dossier contient les datasheets, les notes d'application et les schémas de référence utilisés pour la conception du BMS et de l'étage USB-PD.

## 1. Gestion Batterie & Charge (Charger IC)
*   **IC Principal :** Texas Instruments BQ25713 (NVDC Battery Buck-Boost Charge Controller).
*   **Fichiers :**
    *   `bq25713_datasheet.pdf` : Spécifications complètes.
    *   `bq25713_evm_schematic.pdf` : Schéma de la carte d'évaluation (base de notre design).
    *   `slva928_application_note.pdf` : "Optimizing BQ25713 for USB-PD Applications".

## 2. Microcontrôleur & Logique (RP2350)
*   **MCU :** Raspberry Pi RP2350 (RISC-V / ARM Dual Core).
*   **Fichiers :**
    *   `rp2350_datasheet.pdf` : Pinout et registres.
    *   `hardware_design_with_rp2350.pdf` : Recommandations routage et découplage.

## 3. USB Power Delivery (USB-PD)
*   **IC Contrôleur PD (Sink/Source) :** *[Insérer ici ta ref, ex: HUSB238 ou TPS65987]*
*   **Schémas types :**
    *   `USB-C_PD_Sink_Reference.pdf` : Circuit de négociation 20V.
    *   `ESD_Protection_USB-C.pdf` : Schéma des diodes TVS sur les lignes D+/D-/CC.

## 4. Composants de Puissance (MOSFETs)
*   **Transistors 4S Protection :**
    *   `AON6512_datasheet.pdf` (ou équivalent utilisé).
    *   `Thermal_Calculation_Mosfets.xlsx` : Calcul dissipation thermique.

## 5. Cellules Batterie
*   **Samsung INR18650-35E :**
    *   `Samsung_35E_Datasheet.pdf` : Courbes de décharge 3.7V.
