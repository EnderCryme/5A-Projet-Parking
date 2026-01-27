/**
 * @file main.c
 * @brief Firmware de contrôle d'ascenseur avec recalibrage automatique
 * @author A.Clerville
 * @date 2026-01-27
 * @details Gère un moteur pas-à-pas via un driver TMC5160 en SPI.
 * Inclut la gestion de trois étages, une rampe d'accélération logicielle,
 * un capteur de distance VL53L0X pour le recalage et une sécurité anti-collision.
 */

/* =========================================================================
 * INCLUDES
 * ========================================================================= */
#include <zephyr/kernel.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/sys/printk.h>
#include <zephyr/drivers/sensor.h>
#include <stdlib.h>

/* =========================================================================
 * MACROS & CONFIGURATION
 * ========================================================================= */

/* --- Configuration Étages (mm) --- */
#define HEIGHT_FLOOR_0    0
#define HEIGHT_FLOOR_1    170  
#define HEIGHT_FLOOR_2    336  
#define TOLERANCE_MM      10   

/* --- Réglages Moteur --- */
#define STEPS_PER_MM      350   
#define MAX_SPEED_US      200   
#define MIN_SPEED_US      1200  
#define RAMP_STEPS        2000  

/* --- Sens Moteur --- */
#define DIR_UP            0  
#define DIR_DOWN          1

/* --- Registres TMC5160 --- */
#define REG_GCONF         0x00
#define REG_GSTAT         0x01
#define REG_GLOBAL_SCALER 0x0B
#define REG_IHOLD_IRUN    0x10
#define REG_CHOPCONF      0x6C
#define REG_DRV_STATUS    0x6F

/* =========================================================================
 * MATÉRIEL (Devicetree)
 * ========================================================================= */

#define SPI_OP  (SPI_WORD_SET(8) | SPI_TRANSFER_MSB | SPI_MODE_CPOL | SPI_MODE_CPHA)
const struct spi_dt_spec tmc_spi = SPI_DT_SPEC_GET(DT_NODELABEL(tmc_spi), SPI_OP, 0);

static const struct gpio_dt_spec motor_en   = GPIO_DT_SPEC_GET(DT_ALIAS(motor_enable), gpios);
static const struct gpio_dt_spec motor_dir  = GPIO_DT_SPEC_GET(DT_ALIAS(motor_dir), gpios);
static const struct gpio_dt_spec motor_step = GPIO_DT_SPEC_GET(DT_ALIAS(motor_step), gpios);

/* Boutons */
static const struct gpio_dt_spec btn_stop   = GPIO_DT_SPEC_GET(DT_ALIAS(sw0), gpios);
static const struct gpio_dt_spec btn_f0     = GPIO_DT_SPEC_GET(DT_ALIAS(floor_btn_0), gpios);
static const struct gpio_dt_spec btn_f1     = GPIO_DT_SPEC_GET(DT_ALIAS(floor_btn_1), gpios);
static const struct gpio_dt_spec btn_f2     = GPIO_DT_SPEC_GET(DT_ALIAS(floor_btn_2), gpios);

/* Capteur */
const struct device *const distance_sensor = DEVICE_DT_GET_ANY(st_vl53l0x);

/* =========================================================================
 * FONCTIONS DRIVER TMC5160
 * ========================================================================= */

void tmc_write(uint8_t addr, uint32_t data) {
    uint8_t tx_buf[5];
    tx_buf[0] = addr | 0x80; 
    tx_buf[1] = (data >> 24) & 0xFF;
    tx_buf[2] = (data >> 16) & 0xFF;
    tx_buf[3] = (data >> 8) & 0xFF;
    tx_buf[4] = data & 0xFF;
    struct spi_buf tx = { .buf = tx_buf, .len = 5 };
    struct spi_buf_set tx_set = { .buffers = &tx, .count = 1 };
    spi_write_dt(&tmc_spi, &tx_set);
}

uint32_t tmc_read(uint8_t addr, uint8_t *status_byte) {
    uint8_t tx_buf[5] = { addr, 0, 0, 0, 0 };
    uint8_t rx_buf[5] = { 0 };
    struct spi_buf tx = { .buf = tx_buf, .len = 5 };
    struct spi_buf_set tx_set = { .buffers = &tx, .count = 1 };
    struct spi_buf rx = { .buf = rx_buf, .len = 5 };
    struct spi_buf_set rx_set = { .buffers = &rx, .count = 1 };
    spi_transceive_dt(&tmc_spi, &tx_set, &rx_set);
    if (status_byte) *status_byte = rx_buf[0];
    return (rx_buf[1] << 24) | (rx_buf[2] << 16) | (rx_buf[3] << 8) | rx_buf[4];
}

void configure_tmc_driver(void) {
    tmc_write(REG_GSTAT, 0x00000007);
    tmc_write(REG_GLOBAL_SCALER, 128);
    tmc_write(REG_CHOPCONF, 0x14410153); 
    tmc_write(REG_IHOLD_IRUN, 0x0002100A); 
}

/* =========================================================================
 * LOGIQUE ASCENSEUR
 * ========================================================================= */

bool is_floor_btn_pressed(const struct gpio_dt_spec *btn) {
    if (gpio_pin_get_dt(btn) == 0) { 
        k_sleep(K_MSEC(50)); 
        if (gpio_pin_get_dt(btn) == 0) return true;
    }
    return false;
}

int get_step_delay(int current_step, int total_steps) {
    int delay = MAX_SPEED_US; 
    if (current_step < RAMP_STEPS) {
        delay = MIN_SPEED_US - ((MIN_SPEED_US - MAX_SPEED_US) * current_step / RAMP_STEPS);
    }
    else if (current_step > (total_steps - RAMP_STEPS)) {
        int steps_left = total_steps - current_step;
        delay = MIN_SPEED_US - ((MIN_SPEED_US - MAX_SPEED_US) * steps_left / RAMP_STEPS);
    }
    return delay;
}

/* =========================================================================
 * MAIN
 * ========================================================================= */

int main(void)
{
    printk("\n=== ASCENSEUR : RECALIBRAGE AUTO ===\n");
    k_sleep(K_MSEC(100));

    /* Configuration GPIO */
    gpio_pin_configure_dt(&motor_en, GPIO_OUTPUT_INACTIVE);
    gpio_pin_configure_dt(&motor_dir, GPIO_OUTPUT_LOW);
    gpio_pin_configure_dt(&motor_step, GPIO_OUTPUT_LOW);

    gpio_pin_configure_dt(&btn_stop, GPIO_INPUT);
    gpio_pin_configure_dt(&btn_f0, GPIO_INPUT);
    gpio_pin_configure_dt(&btn_f1, GPIO_INPUT);
    gpio_pin_configure_dt(&btn_f2, GPIO_INPUT);

    /* Setup Driver */
    configure_tmc_driver();
    gpio_pin_set_dt(&motor_en, 1); 
    
    int64_t last_check = k_uptime_get();
    int current_mm = 999; 

    /* === SEQUENCE DE CALIBRAGE (INIT) === */
    printk("-> INITIALISATION...\n");
    gpio_pin_set_dt(&motor_dir, DIR_DOWN); 
    
    while (1) {
        if (gpio_pin_get_dt(&btn_stop) == 1) {
            printk("-> Sol (Bouton). OK.\n");
            gpio_pin_set_dt(&motor_dir, DIR_UP);
            for(int k=0; k<2000; k++) { 
                gpio_pin_set_dt(&motor_step, 1); k_busy_wait(10);
                gpio_pin_set_dt(&motor_step, 0); k_busy_wait(500); 
            }
            break;
        }
        gpio_pin_set_dt(&motor_step, 1); k_busy_wait(10);
        gpio_pin_set_dt(&motor_step, 0); k_busy_wait(300); 
    }
    current_mm = 0; 
    printk("-> PRET.\n");
    
    int target_mm = -1; 
    int next_target_mm = -1; 

    while (1) {
        
        // 1. LECTURE BOUTONS
        int requested_floor = -1;
        if (is_floor_btn_pressed(&btn_f0)) requested_floor = HEIGHT_FLOOR_0;
        else if (is_floor_btn_pressed(&btn_f1)) requested_floor = HEIGHT_FLOOR_1;
        else if (is_floor_btn_pressed(&btn_f2)) requested_floor = HEIGHT_FLOOR_2;

        if (requested_floor != -1) {
            if (target_mm == -1) {
                target_mm = requested_floor;
                printk("-> DEPART: %d mm\n", target_mm);
            }
            else if (target_mm != requested_floor && next_target_mm == -1) {
                next_target_mm = requested_floor;
                printk("-> MEMOIRE: %d mm\n", next_target_mm);
            }
        }

        // 2. MOUVEMENT INTELLIGENT
        if (target_mm != -1) {
            int dist_mm = target_mm - current_mm;
            
            if (abs(dist_mm) < TOLERANCE_MM) {
                 printk("-> Deja sur place.\n");
                 target_mm = -1;
            } 
            else {
                int total_steps = abs(dist_mm) * STEPS_PER_MM;
                printk("-> Trajet: %d mm (%d pas)\n", dist_mm, total_steps);

                if (dist_mm > 0) gpio_pin_set_dt(&motor_dir, DIR_UP);
                else gpio_pin_set_dt(&motor_dir, DIR_DOWN);

                for(int i = 0; i < total_steps; i++) {
                    int dynamic_delay = get_step_delay(i, total_steps);

                    gpio_pin_set_dt(&motor_step, 1);
                    k_busy_wait(10);
                    gpio_pin_set_dt(&motor_step, 0);
                    k_busy_wait(dynamic_delay); 

                    // --- STOP & RECALIBRAGE ---
                    if (gpio_pin_get_dt(&btn_stop) == 1) {
                        if (dist_mm < 0) {
                            printk("-> SOL TOUCHE : Recalibrage Auto !\n");
                            gpio_pin_set_dt(&motor_dir, DIR_UP);
                            for(int k=0; k<3500; k++) {
                                gpio_pin_set_dt(&motor_step, 1); k_busy_wait(10);
                                gpio_pin_set_dt(&motor_step, 0); k_busy_wait(500);
                            }
                            current_mm = 0; 
                            target_mm = -1; 
                            break; 
                        } 
                        else {
                            printk("!!! STOP URGENCE (Montee) !!!\n");
                            target_mm = -1;
                            break;
                        }
                    }
                }
            }

            if (target_mm == -1) {
                next_target_mm = -1; 
            } else {
                current_mm = target_mm;
                printk("-> ARRIVÉ THEORIQUE (%d mm).\n", current_mm);
                
                if (device_is_ready(distance_sensor)) {
                    struct sensor_value value;
                    if (sensor_sample_fetch(distance_sensor) == 0) {
                        sensor_channel_get(distance_sensor, SENSOR_CHAN_DISTANCE, &value);
                        int real_mm = (value.val1 * 1000) + (value.val2 / 1000);
                        if (abs(real_mm - current_mm) < 50) current_mm = real_mm;
                    }
                }

                k_sleep(K_MSEC(500)); 

                if (next_target_mm != -1) {
                    printk("-> ENCHAINEMENT: %d mm\n", next_target_mm);
                    target_mm = next_target_mm; 
                    next_target_mm = -1;        
                } else {
                    target_mm = -1; 
                    printk("-> En attente.\n");
                }
            }
        } 
        else {
            k_sleep(K_MSEC(10));
        }

        // 3. RESILIENCE
        if (k_uptime_get() - last_check > 2000) {
            last_check = k_uptime_get();
            uint8_t status = 0;
            tmc_read(REG_DRV_STATUS, &status);
            if ((status & 0x01) || (status & 0x02)) {
                configure_tmc_driver(); 
                gpio_pin_set_dt(&motor_en, 1);
            }
        }
    }
    return 0;
}