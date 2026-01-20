#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <mosquitto.h>

// --- CONFIGURATION ---
#define BROKER_IP    "192.168.1.100"
#define BROKER_PORT  1883
#define TOPIC        "parking/barrier"
#define MOTOR_ADDR   0xF0000000

// --- CALIBRAGE ---
// Tu as déterminé que 128 cycles suffisent pour l'ouverture
#define CYCLES_REQUIRED 128 
#define STEP_DELAY      2500 // 2.5ms (Vitesse moyenne/fluide)

volatile unsigned int *motor_reg = NULL;
struct mosquitto *mosq = NULL;

// Etat de la barrière : 0 = FERMÉE (Position de départ), 1 = OUVERTE
int is_open = 0; 

// Séquences
int seq_open[]  = {1, 2, 4, 8}; 
int seq_close[] = {8, 4, 2, 1};

void set_motor_bits(int val) {
    if (motor_reg) *motor_reg = val;
}

// Fonction de mouvement
void move_barrier(int open_cmd) {
    // 1. Sécurité : Vérifier si on doit vraiment bouger
    if (open_cmd == 1 && is_open == 1) {
        printf(">>> Barrière déjà OUVERTE. Ignoré.\n");
        return;
    }
    if (open_cmd == 0 && is_open == 0) {
        printf(">>> Barrière déjà FERMÉE. Ignoré.\n");
        return;
    }

    // 2. Préparation
    int *current_seq = (open_cmd) ? seq_open : seq_close;
    printf(">>> Action : %s (128 Cycles)...\n", open_cmd ? "OUVERTURE" : "FERMETURE");

    // 3. Exécution du mouvement
    for (int i = 0; i < CYCLES_REQUIRED; i++) {
        for (int step = 0; step < 4; step++) {
            set_motor_bits(current_seq[step]);
            usleep(STEP_DELAY);
        }
    }

    // 4. Fin et Mise à jour de l'état
    set_motor_bits(0); // Couper le courant (important !)
    is_open = open_cmd; // On met à jour l'état (0 ou 1)
    
    printf(">>> Terminé. Barrière est maintenant %s.\n", is_open ? "OUVERTE" : "FERMÉE");
}

void on_message(struct mosquitto *m, void *userdata, const struct mosquitto_message *msg) {
    if (msg->payloadlen == 0) return;
    char *text = (char *)msg->payload;
    
    printf("[MQTT] Recu : %s\n", text);

    if (strncmp(text, "OPEN", 4) == 0) {
        move_barrier(1);
    } 
    else if (strncmp(text, "CLOSE", 5) == 0) {
        move_barrier(0);
    }
}

int main() {
    // MAPPING
    int mem_fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (mem_fd < 0) return 1;
    void *map_base = mmap(0, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, mem_fd, MOTOR_ADDR & ~0xFFF);
    if (map_base == MAP_FAILED) return 1;
    motor_reg = (volatile unsigned int *)(map_base + (MOTOR_ADDR & 0xFFF));

    // MQTT
    mosquitto_lib_init();
    mosq = mosquitto_new("barrier_final", true, NULL);
    if (!mosq) return 1;

    mosquitto_message_callback_set(mosq, on_message);

    if (mosquitto_connect(mosq, BROKER_IP, BROKER_PORT, 60) != MOSQ_ERR_SUCCESS) {
        fprintf(stderr, "Erreur connexion broker.\n");
        return 1;
    }

    mosquitto_subscribe(mosq, NULL, TOPIC, 0);

    printf("=== SYSTEME BARRIERE OPÉRATIONNEL ===\n");
    printf("Etat initial : FERMÉE\n");
    printf("En attente de commandes OPEN / CLOSE...\n");

    mosquitto_loop_forever(mosq, -1, 1);

    return 0;
}