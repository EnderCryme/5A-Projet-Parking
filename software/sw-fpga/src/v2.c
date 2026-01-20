#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <ctype.h>
#include <sys/mman.h>
#include <mosquitto.h>

// --- CONFIGURATION ---
#define BROKER_IP   "192.168.1.100"
#define BROKER_PORT 1883
#define TOPIC       "parking/test"
#define MOTOR_ADDR  0xF0000000  // Ton adresse confirmée

// Vitesse (2ms par pas = assez rapide)
#define STEP_DELAY  2000 

volatile unsigned int *motor_reg = NULL;
struct mosquitto *mosq = NULL;

// Séquence 4 pas (1 cycle complet = 4 changements d'état)
int seq_p[] = {1, 2, 4, 8}; // Sens Positif
int seq_m[] = {8, 4, 2, 1}; // Sens Inverse (Minus)

void set_motor_bits(int val) {
    if (motor_reg) *motor_reg = val;
}

// Fonction qui exécute X cycles
// direction : 1 pour Positif (p), 0 pour Minus (m)
void run_cycles(int cycles, int direction) {
    int *current_seq = (direction) ? seq_p : seq_m;
    
    printf(">>> Execution de %d cycles (Sens: %s)...\n", cycles, direction ? "POSITIF" : "INVERSE");
    
    // Pour chaque cycle demandé
    for (int i = 0; i < cycles; i++) {
        // On joue les 4 étapes de la séquence
        for (int step = 0; step < 4; step++) {
            set_motor_bits(current_seq[step]);
            usleep(STEP_DELAY);
        }
    }
    
    // Sécurité : On coupe le moteur à la fin
    set_motor_bits(0);
    printf(">>> Termine.\n");
}

void on_message(struct mosquitto *m, void *userdata, const struct mosquitto_message *msg) {
    if (msg->payloadlen == 0) return;
    
    // On récupère le message (ex: "p64" ou "m128")
    char *text = (char *)msg->payload;
    char cmd = text[0]; // La première lettre ('p' ou 'm')
    
    // On lit le nombre qui suit la lettre (à partir du 2ème caractère)
    // atoi va ignorer la lettre si on lui donne l'adresse suivante
    int val = atoi(&text[1]); 
    
    if (val <= 0) {
        printf("[Erreur] Nombre de cycles invalide : %s\n", text);
        return;
    }

    if (cmd == 'p' || cmd == 'P') {
        run_cycles(val, 1); // 1 = Positif
    } 
    else if (cmd == 'm' || cmd == 'M') {
        run_cycles(val, 0); // 0 = Inverse
    }
    else {
        printf("[Erreur] Commande inconnue. Utilisez pXXX ou mXXX (ex: p64)\n");
    }
}

int main() {
    // 1. MAPPING MEMOIRE
    int mem_fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (mem_fd < 0) return 1;
    void *map_base = mmap(0, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, mem_fd, MOTOR_ADDR & ~0xFFF);
    if (map_base == MAP_FAILED) return 1;
    motor_reg = (volatile unsigned int *)(map_base + (MOTOR_ADDR & 0xFFF));

    // 2. INIT MQTT
    mosquitto_lib_init();
    mosq = mosquitto_new("test_client", true, NULL);
    if (!mosq) return 1;

    mosquitto_message_callback_set(mosq, on_message);

    if (mosquitto_connect(mosq, BROKER_IP, BROKER_PORT, 60) != MOSQ_ERR_SUCCESS) {
        fprintf(stderr, "Erreur connexion broker\n");
        return 1;
    }

    mosquitto_subscribe(mosq, NULL, TOPIC, 0);

    printf("--- MODE TEST MOTEUR ---\n");
    printf("Envoyez 'p64' pour 64 cycles positifs\n");
    printf("Envoyez 'm128' pour 128 cycles inversés\n");
    printf("En attente...\n");

    mosquitto_loop_forever(mosq, -1, 1);

    return 0;
}
