# Prototype VHDL (FPGA) — Pilotage moteur de barrière + capteur + buzzer

Ce document décrit un prototype VHDL implémenté sur FPGA pour piloter un moteur pas-à-pas via ULN2003, avec sélection de vitesse, sens de rotation, autorisation par capteur de présence et retours utilisateurs (LEDs + buzzer).  
Ce bloc a été pensé comme une base matérielle réutilisable dans une logique d’intégration SoC (ex. MicroBlaze).

---

## 1. Objectif

- Générer les **4 phases** de commande moteur (`phases[3:0]`)
- Piloter :
  - **marche/arrêt** (`enable`)
  - **sens** (`direction`)
  - **vitesse** (`speed_sel` sur 4 niveaux)
- Ajouter un interverrouillage simple : **le moteur tourne uniquement si présence détectée**
- Fournir un retour :
  - LED présence
  - LED direction
  - buzzer (~2 kHz) lorsque le moteur est actif

---

## 2. Organisation du design

Le design est composé de 3 modules :

- `barrier_motor_top` : intégration et logique de commande
- `step_clock_sel` : génération d’un tick `step_ce` selon `speed_sel`
- `fsm_hightorque` : séquenceur de phases moteur (4 états)

Chaîne fonctionnelle :

1. `prox_sensor` (1 = présence) autorise la rotation
2. `step_clock_sel` génère `step_ce` (impulsion 1 cycle) à la fréquence choisie
3. `fsm_hightorque` avance d’un état à chaque tick et met à jour `phases`

---

## 3. Interfaces (ports)

### 3.1 Entrées
- `clk` : horloge 100 MHz
- `reset` : reset actif haut
- `enable` : autorisation
- `direction` : sens
- `speed_sel[1:0]` : sélection vitesse
- `prox_sensor` : présence (1 = détecté)

### 3.2 Sorties
- `phases[3:0]` : vers ULN2003 IN1..IN4
- `led_sensor` : témoin présence
- `led_dir` : témoin direction effective
- `buzzer_out` : buzzer (~2 kHz) lorsque moteur actif

---

## 4. Description des modules

### 4.1 `barrier_motor_top`
- `motor_enable <= enable AND prox_sensor`
- Synchronisation de `direction` sur 2 bascules + inversion optionnelle (`INVERT_DIR`)
- Buzzer carré ~2 kHz uniquement si moteur actif
- Instancie `step_clock_sel` et `fsm_hightorque`

### 4.2 `step_clock_sel`
Génère `step_ce` (impulsion 1 cycle) en divisant 100 MHz :

- `00` → 100 Hz  
- `01` → 200 Hz  
- `10` → 400 Hz  
- `11` → 800 Hz  

### 4.3 `fsm_hightorque`
FSM 4 états (2 phases actives) :

| État | `phases` |
|---|---|
| `s3`  | `0011` |
| `s6`  | `0110` |
| `s9`  | `1100` |
| `s12` | `1001` |

L’état change uniquement si `enable=1` et `step_ce=1`.  
Le sens dépend de `direction`.

---

## 5. Génération du bitstream (Vivado)

1. Créer un projet Vivado
2. Ajouter :
   - `barrier_motor_top.vhd`
   - `step_clock_sel.vhd`
   - `fsm_hightorque.vhd`
3. Ajouter le fichier de contraintes : `constraints/nexys4ddr_barrier.xdc`
4. Synthesis → Implementation → Generate Bitstream
5. Programmer la carte

---

## 6. Tests rapides

- `enable=0` → moteur arrêté, buzzer off
- `enable=1` et `prox_sensor=0` → moteur arrêté, buzzer off
- `enable=1` et `prox_sensor=1` → moteur actif, buzzer on
- modifier `speed_sel` → variation de vitesse
- modifier `direction` → inversion du sens

---

# Pinout (Nexys4DDR)

IO standard : **LVCMOS33** — Horloge : **E3 (100 MHz)**

## Horloge / Reset

| Signal | Broche |
|---|---:|
| `clk` | E3 |
| `reset` | N17 |

## Switches

| Signal | Switch | Broche |
|---|---:|---:|
| `enable` | SW0 | J15 |
| `direction` | SW1 | L16 |
| `speed_sel[0]` | SW2 | M13 |
| `speed_sel[1]` | SW3 | R15 |

## Capteur

| Signal | Connecteur | Broche |
|---|---|---:|
| `prox_sensor` | JB1 | D14 |

## LEDs / Buzzer

| Signal | Sortie | Broche |
|---|---|---:|
| `led_sensor` | LED0 | H17 |
| `led_dir` | LED1 | K15 |
| `buzzer_out` | JD10 | F3 |

## Phases moteur (ULN2003)

| Signal | Broche |
|---|---:|
| `phases[0]` | C17 |
| `phases[1]` | D18 |
| `phases[2]` | E18 |
| `phases[3]` | G17 |

> Note : l’ordre exact des phases dépend du câblage ULN2003/moteur.  
> Si besoin, inverser via `INVERT_DIR` ou permuter les fils.

