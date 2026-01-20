
# Guide : Activer le Dual-Core (SMP) sur Linux-on-LiteX-VexRiscv

Ce document résume les modifications nécessaires pour faire tourner Linux sur un SoC LiteX avec 2 cœurs VexRiscv (SMP) sur une carte Nexys4DDR (adaptable aux autres cartes).

## 1. Génération du Matériel (Gateware)

Compiler le bitstream en spécifiant 2 CPUs. Cela modifie la carte mémoire et les adresses des périphériques.

```bash
./make.py --board=nexys4ddr --cpu-count=2 --build
```

> **Note :** Cette étape génère un fichier DTS de base dans `build/nexys4ddr/dts/nexys4ddr.dts`, mais il est souvent incomplet (manque le 2ème CPU).

## 2. Modification du Device Tree (DTS)

Le fichier `.dts` généré automatiquement ne déclare souvent que le CPU0. Il faut éditer manuellement `build/nexys4ddr/dts/nexys4ddr.dts`.

### A. Ajouter le CPU1

Dans la section `cpus { ... }`, copier le bloc `cpu@0` et le modifier pour créer `cpu@1`.
**Important :** Il faut définir un label unique pour le contrôleur d'interruption (ici `L1`).

```dts
        /* ... après la fermeture de cpu@0 ... */
        CPU1: cpu@1 {
            device_type = "cpu";
            compatible = "riscv";
            riscv,isa = "rv32i2p0_ma";
            riscv,isa-base = "rv32i";
            riscv,isa-extensions = "a", "i", "m";
            mmu-type = "riscv,sv32";
            reg = <1>;           /* ID du CPU */
            clock-frequency = <75000000>;
            status = "okay";
            
            /* ... caches et TLBs identiques au CPU0 ... */
            d-cache-size = <4096>; 
            /* ... etc ... */

            /* Label L1 pour le contrôleur d'interruption du CPU1 */
            L1: interrupt-controller {
                #address-cells = <0>;
                #interrupt-cells = <0x00000001>;
                interrupt-controller;
                compatible = "riscv,cpu-intc";
            };
        };

```

### B. Mettre à jour le CLINT (Timer & Soft IRQ)

Chercher le bloc `riscv,clint0` (souvent label `lintc0`) et ajouter les références au CPU1 (`&L1`).

```dts
        lintc0: clint@f0010000 {
            compatible = "riscv,clint0";
            /* Ajouter &L1 3 &L1 7 pour le second coeur */
            interrupts-extended = <&L0 3 &L0 7 &L1 3 &L1 7>;
            reg = <0xf0010000 0x10000>;
            reg-names = "control";
        };

```

### C. Mettre à jour le PLIC (Périphériques Externes)

Chercher le bloc `sifive,plic-1.0.0` (souvent label `intc0`) et ajouter les références au CPU1.

```dts
        intc0: interrupt-controller@f0c00000 {
            compatible = "sifive,fu540-c000-plic", "sifive,plic-1.0.0";
            /* Ajouter &L1 11 &L1 9 pour le second coeur (Machine/Supervisor external) */
            interrupts-extended = <&L0 11 &L0 9 &L1 11 &L1 9>;
            /* ... le reste ne change pas ... */
        };

```

## 3. Compilation du Device Tree (DTB)

Transformer le fichier source modifié (`.dts`) en binaire (`.dtb`) et le placer dans le dossier des images.

```bash
dtc -O dtb -o images/nexys4ddr.dtb build/nexys4ddr/dts/nexys4ddr.dts

```

## 4. Configuration du Boot (boot.json)

Vérifier dans le fichier `.dts` l'adresse définie par `linux,initrd-start`.
Exemple trouvé : `<0x41000000>`.

Modifier `images/boot.json` pour aligner l'adresse de chargement du `rootfs` avec celle attendue par le DTS.

```json
{
    "Image":         "0x40000000",
    "nexys4ddr.dtb": "0x40ef0000",
    "rootfs.cpio":   "0x41000000",  <-- Doit correspondre au linux,initrd-start du DTS
    "fw_jump.bin":   "0x40f00000"
}

```

## 5. Chargement et Test

Charger le système via le port série.

```bash
python3 make.py --board=nexys4ddr --load

```

Une fois logué dans Linux, vérifier la présence des deux cœurs :

```bash
cat /proc/cpuinfo

```

Le résultat doit afficher `processor : 0` et `processor : 1` tel que :
```bash
# cat /proc/cpuinfo
processor       : 0
hart            : 0
isa             : rv32i2p0_ma
mmu             : sv32

processor       : 1
hart            : 1
isa             : rv32i2p0_ma
mmu             : sv32
```

## 6. Flasher le nouveau firmware :

Vivado a généré un fichier .bit (utilisé pour charger le FPGA temporairement). Mais pour flasher la puce mémoire (SPI Flash) et rendre la configuration permanente, OpenOCD a besoin d'un fichier .bin.

Il faut donc convertir le .bit en .bin manuellement via Vivado.
Pour cela nous allons générer un script `gen_bin.tcl`: 

### 1. Création du script de conversion

```bash
cat <<EOF > gen_bin.tcl
write_cfgmem -force -format bin -interface SPIx1 -size 16 -loadbit "up 0x0 ./build/nexys4ddr/gateware/nexys4ddr.bit" -file ./build/nexys4ddr/gateware/nexys4ddr.bin
exit
EOF
```

> **Note :** Cette commande génère un script TCL pour Vivado. Elle utilise l'outil `write_cfgmem` pour transformer le bitstream FPGA (`.bit`) en une image mémoire brute (`.bin`) compréhensible par le programmateur de flash.
> * **`-interface SPIx1`** : Indispensable ici pour correspondre à la configuration par défaut du bitstream (Single SPI). Si on mettait `SPIx4` (Quad-SPI), Vivado rejetterait le fichier car le design n'a pas été explicitement compilé pour le mode x4.
> * **`-size 16`** : Spécifie la taille de la puce mémoire de la Nexys4DDR (16 Mo).
> * **`up 0x0`** : Place la configuration du FPGA au tout début de la mémoire Flash.
> 
> 

### 2. Exécution de Vivado

```bash
vivado -mode tcl -source gen_bin.tcl

```

> **Note :** Cette commande lance Vivado en mode "TCL" (Terminal/Ligne de commande), sans charger l'interface graphique lourde. Elle exécute immédiatement les instructions du fichier `gen_bin.tcl` créé précédemment. C'est la méthode standard pour automatiser des tâches Vivado dans un terminal Linux.

---

### 3. Flashage (Rappel)

```bash
python3 make.py --board=nexys4ddr --flash

```

> **Note :** Cette commande utilise OpenOCD pour écrire le fichier `.bin` généré dans la mémoire non-volatile (SPI Flash) de la carte. Au prochain redémarrage électrique, le FPGA chargera cette configuration automatiquement.
> **Attention :** Seul le Gateware (SoC + CPU) est flashé. Le noyau Linux et le système de fichiers (`rootfs`, `Image`, `dtb`) doivent être placés sur la carte SD pour un démarrage autonome.
