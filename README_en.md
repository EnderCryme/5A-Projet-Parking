# 🅿️ Modular Smart Parking System (PSM)

![Status](https://img.shields.io/badge/Status-Functional_Prototype-success)
![Architecture](https://img.shields.io/badge/Architecture-Distributed_IoT-blueviolet)

**Platforms:**
![BeagleY-AI](https://img.shields.io/badge/Brain-BeagleY--AI-blue)
![STM32](https://img.shields.io/badge/Edge-STM32F746-green)
![FPGA](https://img.shields.io/badge/Control-Nexys_A7--100T-orange)

**Tech Stack:**
![Languages](https://img.shields.io/badge/Code-C_%7C_Python_%7C_Verilog-lightgrey)
![OS](https://img.shields.io/badge/OS-Linux_%7C_Zephyr_RTOS-yellow)
![Protocol](https://img.shields.io/badge/Com-MQTT_%7C_Ethernet-red)

---

## 👥 Project Team
* **FALDA Andy**
* **CAUQUIL Vincent**
* **ES-SRIEJ Youness**
* **CLERVILLE Annabelle**

---

## 📖 Project Description

This project implements a complete smart parking management ecosystem. It demonstrates a distributed architecture where each module (Brain, Interface, Actuator) communicates over a local network using the **MQTT** protocol.

The system combines:
1. **Artificial Intelligence (OCR)** for Automatic Number Plate Recognition (ANPR).
2. **Real-Time System (Zephyr RTOS)** for user interaction and RFID management.
3. **Hardware Acceleration (FPGA/RISC-V SoC)** for precise control of motorized barriers.

---

## 🛠 Architecture & Network

The system operates on a closed local Ethernet network. The **BeagleY-AI** serves as the central node (MQTT Broker & Web Server).

### 🌐 IP Configuration (Static)

| Module | Role | OS / Firmware | IP Address |
| :--- | :--- | :--- | :--- |
| **BeagleY-AI** | **Brain**: MQTT Broker, OCR, Web Dashboard | Linux (Debian) | `192.168.78.2` |
| **STM32 F7** | **Entry**: RFID, Touchscreen, Sensors | Zephyr RTOS | `192.168.78.3` |
| **FPGA Nexys** | **Motors**: Barrier Drivers, Custom SoC | Linux (Buildroot) | `192.168.78.10` |

### 📡 MQTT Topic Flow

| Topic | Source | Destination | Description |
| :--- | :--- | :--- | :--- |
| `RFID/ID` | STM32 | BeagleY | Sends scanned RFID badge UID. |
| `RFID/CMD` | BeagleY | STM32 | Access response (`UNLOCK` / `DENY`). |
| `parking/barrier` | BeagleY | FPGA | Physical open/close command. |
| `video/stream` | BeagleY | Dashboard | Real-time camera video feed. |

---

## 📂 Repository Structure

```text
├── gateware/                # 🧱 FPGA (Programmable Logic)
│   └── fpga/                # LiteX SoC + VexRiscv sources
│
├── hardware/                # ⚙️ Mechanical & PCB Design
│   ├── model3D/             # Onshape CAD files (Barriers, enclosures)
│   └── pcb-designs/         # Daughterboard schematics
│
├── software/                # 💻 Source Code
│   ├── sw-BBY-camera/       # [Python] Server, OpenCV, Tesseract
│   ├── sw-FPGA-barrieres/   # [C/Linux] Motor drivers for FPGA SoC
│   ├── sw-STM32-elevator/   # [C/Zephyr] Elevator management
│   └── sw-STM32-rfid/       # [C/Zephyr] Main Entry management (RFID/UI)
│
└── references/              # 📚 Technical Documentation & Project PDF
```

---

## 🧩 Module Details

### 1. BeagleY-AI (The Brain)
* **Image Processing:** Uses **OpenCV** (localization, cropping) and **Tesseract** (OCR) to extract license plate numbers.
* **Voting Algorithm:** Validates plates across 3 consecutive images (majority vote) to improve reading reliability.
* **Dashboard:** Locally hosted HTML/CSS web interface for video monitoring and parking status.

### 2. STM32F746 (The Physical Interface)
* **Identification:** RC522 RFID reader on SPI bus.
* **Interaction:** Touchscreen UI developed with **LVGL** (user feedback, error codes).
* **Power Management:** Ambient light sensor for brightness control and automatic screen shutdown when no vehicle is detected.
* **Security:** Hardcoded "Master" badge for forced opening or maintenance menu access.

### 3. FPGA Nexys A7 (The Powerhouse)
* **Custom SoC:** Implementation of a **32-bit RISC-V** processor on FPGA using LiteX.
* **Embedded Linux:** The FPGA runs a minimal Linux kernel capable of mapping motor peripherals via `mmap`.
* **Motor Control:** Power control for barriers via SoC-driven external drivers.

---

## 🚀 Installation & Quick Start

### Prerequisites
* **Network:** Router or switch configured for `192.168.78.x` subnet.
* **Tools:**
    * [STM32] **West** (Zephyr Toolchain)
    * [FPGA] **Vivado** (Xilinx Lab Tools)
    * [Beagle] **Python 3**

### Quick Start Guide

1. **BeagleY-AI (Server Startup):**
    ```bash
    cd software/sw-BBY-camera
    python3 main.py
    ```

2. **STM32 (Build & Flash):**
    ```bash
    # From project root
    west build -b stm32f746g_disco software/sw-STM32-rfid
    west flash
    ```

3. **FPGA (Bitstream & Boot):**
    * Open Vivado Hardware Manager.
    * Load the bitstream from `gateware/fpga/v3-test-autorun`.
    * *Result:* The SoC boots, loads Linux from the SD card, and automatically joins the network.

4. **BMS (MicroPython Flashing):**
    * **Reset:** Hold **SW2** (USB_BOOT) and connect the RP2350 via USB.
    * **Firmware:** Copy the Pico 2 `.uf2` file (available at [micropython.org](https://micropython.org/download/RPI_PICO2/)) to the `RPI-RP3` drive.
    * **Code:** Use **Thonny IDE** to transfer `ssd1306.py` and `main.py` to the root.
    * *Note:* `main.py` runs automatically on battery power thanks to autorun.

---

## 📚 References
* [Complete Documentation (PDF)](references/Projet_CAUQUIL_FALDA_CLERVILLE_ES-SRIEJ.pdf)
* [LiteX - Linux on RISC-V](https://github.com/litex-hub/linux-on-litex-vexriscv)
* [Battery Management ICs](https://www.ti.com/product-category/battery-management-ics/overview.html)

7. Ensured consistent terminology throughout the document

The English version is now fully synchronized with the French version while maintaining technical accuracy.
