```bash
at > configs/litex_vexriscv_defconfig <<EOF
# --- ARCHITECTURE (STRICTE rv32ima) ---
BR2_riscv=y
BR2_RISCV_32=y

# Architecture manuelle pour correspondre au FPGA
BR2_RISCV_ISA_CUSTOM_RVI=y
BR2_RISCV_ISA_CUSTOM_RVM=y
BR2_RISCV_ISA_CUSTOM_RVA=y
# On DESACTIVE tout ce que le processeur n'a pas (Vital pour éviter SIGILL)
# BR2_RISCV_ISA_CUSTOM_RVC is not set
# BR2_RISCV_ISA_CUSTOM_RVF is not set
# BR2_RISCV_ISA_CUSTOM_RVD is not set

# ABI : On force les entiers (Soft Float)
BR2_RISCV_ABI_ILP32=y

# --- SYSTEME ---
BR2_TARGET_GENERIC_HOSTNAME="litex-c"
BR2_TARGET_GENERIC_ISSUE="Welcome to LiteX (C Version)"
BR2_SYSTEM_DHCP="eth0"
BR2_TARGET_ROOTFS_CPIO=y

# --- PAQUETS ---
# MQTT (Indispensable)
BR2_PACKAGE_MOSQUITTO=y
BR2_PACKAGE_MOSQUITTO_BROKER=y
BR2_PACKAGE_MOSQUITTO_CLIENT=y

# Editeur de texte (Pratique pour débugger des scripts sh)
BR2_PACKAGE_NANO=y
EOF
```


```bash
make litex_vexriscv_defconfig
make clean
make
```
> **Note** : si vous travaillez sous WSL il est possible que l'erreur suivante apparaise :
> ```bash
> Your PATH contains spaces, TABs, and/or newline (\n) characters.
> This doesn't work. Fix your PATH environment variable.
> make: *** [support/dependencies/dependencies.mk:27: dependencies] Error 1```

> **Note** : Pour la résoudre il faut modifier vos variables d'envrionnement tel que : 
> ```bash
> export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin```
