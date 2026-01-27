# SoC MicroBlaze + IP “barrière” (AXI) — Nexys A7

L’objectif était d’intégrer le pilotage de la barrière dans un SoC sur FPGA : **MicroBlaze** pour la supervision et la logique “haut niveau”, et un bloc matériel dédié pour les fonctions **temps-réel** (commande moteur, prise en compte capteurs, signaux d’indication). Cette approche permettait d’obtenir une implémentation plus **spécifique** et **optimisée** pour le besoin du projet.

---

## 1. Intérêt de l’approche SoC

- **Spécialisation de l’interface** : exposition de commandes/états strictement utiles (registres dédiés au pilotage).
- **Déterminisme** : exécution des actions critiques (timing, sécurité) au niveau matériel.
- **Modularité** : séparation claire entre décisions haut niveau (CPU) et exécution temps-réel (FPGA).
- **Évolutivité** : ajout de fonctionnalités côté logiciel sans modifier la logique matérielle de base, tant que l’interface AXI reste stable.

---

## 2. Fonctionnalités couvertes par le bloc “barrière” (niveau système)

Le bloc matériel regroupe les fonctions nécessaires au pilotage local de la barrière :

- Commande actionneur (ex. moteur pas à pas via sorties **4 phases**)
- Lecture d’un capteur de présence (proximité)
- Condition d’autorisation : activation moteur uniquement si **enable** ET **présence détectée**
- Sélection de vitesse (2 bits)
- Gestion du sens (direction) avec synchronisation
- Indicateurs : LED capteur, LED direction, buzzer (activité)

### Repères Nexys A7 (signaux)
- `clk` : 100 MHz  
- `reset` : bouton (actif haut)  
- `enable`, `direction`, `speed_sel[1:0]` : switches  
- `prox_sensor` : entrée capteur (1 = présence)  
- `phases[3:0]` : sorties driver (type ULN2003)  
- `buzzer_out` : buzzer  

---

## 3. Architecture du SoC (Vivado Block Design)

Le SoC est construit avec l’IP Integrator (Vivado) autour des éléments suivants :

- **MicroBlaze**
- **BRAM** + contrôleur (mémoire instructions/données)
- **AXI Interconnect**
- Périphériques AXI usuels (UARTLite, GPIO, Timer…)
- IP custom **`barrier_ctrl` (AXI4-Lite)** pour l’interface CPU ↔ bloc barrière

Principe d’échange :

1. Écriture de commandes via registres AXI-Lite (`CTRL`, `SPEED`, …)
2. Exécution matérielle temps-réel au niveau de l’IP
3. Lecture de l’état et des capteurs (`STATUS`, `SENSORS`, …)
4. Option : interruptions (IRQ) pour signaler des événements (timeout, anomalie, etc.)

---

## 4. IP `barrier_ctrl` : interface AXI-Lite (registre map)

Le choix a été de proposer une interface volontairement simple et dédiée au projet.

| Registre | Type | Description |
|---|---:|---|
| `CTRL` | W | activation / commande (start/stop) / options |
| `SPEED` | W | sélection vitesse (2 bits) |
| `STATUS` | R | état global (ready/running/fault + sens actif…) |
| `SENSORS` | R | image des capteurs (proximité, etc.) |
| `CFG` | R/W | paramètres (ex : inversion sens, options sécurité) |

Comportements clés (implémentés côté matériel) :
- Autorisation moteur conditionnée par `enable` **et** `prox_sensor`
- Synchronisation de la direction (robustesse vis-à-vis des entrées externes)
- Activation du buzzer lors de l’activité moteur

---

## 5. Mise en place Gateware (Vivado)

### A. Assemblage du Block Design
- Ajout MicroBlaze
- Ajout BRAM + controller
- Ajout AXI Interconnect
- Ajout UARTLite (console) et/ou GPIO si nécessaire
- Intégration de `barrier_ctrl` (AXI4-Lite)

### B. Points d’attention
- Propagation correcte des signaux clock/reset
- Attribution des adresses AXI (Address Editor)
- Connexion des ports externes (capteur, phases moteur, buzzer, LEDs)

### C. Contraintes (XDC) Nexys A7
- Horloge 100 MHz
- Bouton reset
- Switches de commande
- GPIO capteur
- Sorties phases + buzzer + LEDs

---

## 6. Génération du bitstream et export matériel (XSA)

Flux Vivado :

- Synthesis → Implementation → Generate Bitstream
- Export hardware (incluant le bitstream) → génération du `.xsa`

Le fichier `.xsa` sert de base à la création de la plateforme côté Vitis.

---

## 7. Côté logiciel (Vitis) : scénario minimal visé

Un programme baremetal de validation suffisait pour confirmer l’intégration :

- Initialisation UART
- Écriture `CTRL` et `SPEED`
- Lecture `STATUS` et `SENSORS` en boucle
- Option : gestion IRQ si activée

---

## 8. Évolution du projet

L’approche MicroBlaze était pertinente pour obtenir une solution **sur-mesure** et optimisée. Dans le contexte du projet, la suite n’a pas été poursuivie jusqu’à une intégration complète côté Vitis, et une autre orientation a été retenue pour la continuité.

---

## 9. Debug recommandé

- LEDs : indicateurs d’état (présence/direction/activité)
- UART : traces côté CPU
- ILA : observation des transactions AXI et des signaux internes de l’IP

---

## Annexes

### Checklist rapide (Vivado)
- Adresses AXI cohérentes (Address Editor)
- Clock/reset propagés correctement
- XDC complet (pins + IOSTANDARD)
- Export `.xsa` avec bitstream
