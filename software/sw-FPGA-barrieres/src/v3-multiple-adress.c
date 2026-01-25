#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <mosquitto.h>

// --- CONFIGURATION GENERALE ---
#define BROKER_IP    "192.168.1.100"
#define BROKER_PORT  1883
#define BASE_TOPIC   "parking/barrier" 

// --- CONFIGURATION ADRESSES (Selon ton CSR.CSV) ---
// Index 0 et 1 = Connecteur JA
// Index 2 et 3 = Connecteur JB (si câblé plus tard)
unsigned int BARRIER_ADDRS[] = {
    0xF0000000, // ID 0 : PMOD JA (Haut - Pins 1-4)
    0xF0000800, // ID 1 : PMOD JA (Bas  - Pins 7-10)
    0xF0002000, // ID 2 : PMOD JB (Haut)
    0xF0002800  // ID 3 : PMOD JB (Bas)
};

// --- CALIBRAGE MOTEUR ---
#define CYCLES_REQUIRED 128
#define STEP_DELAY      2500 

// Variables Globales
volatile unsigned int *motor_reg = NULL;
struct mosquitto *mosq = NULL;

// Etat de la barrière
int barrier_id = 0;      // ID de la barrière
int is_open = 0;         // 0 = Fermée, 1 = Ouverte
int invert_sens = 0;     // 0 = Normal (Gauche), 1 = Inversé (Droite)

// Séquences physiques
int seq_cw[]  = {1, 2, 4, 8}; // Clockwise (Sens A)
int seq_ccw[] = {8, 4, 2, 1}; // Counter-Clockwise (Sens B)

void set_motor_bits(int val) {
    if (motor_reg) *motor_reg = val;
}

// Fonction de mouvement
void move_barrier(int open_cmd) {
    // 1. Vérification d'état
    if (open_cmd == is_open) {
        printf("[ID:%d] Deja dans la bonne position. Ignore.\n", barrier_id);
        return;
    }

    printf("[ID:%d] Action : %s (Sens: %s)\n", 
            barrier_id, 
            open_cmd ? "OUVERTURE" : "FERMETURE",
            invert_sens ? "INVERSE" : "NORMAL");

    // 2. Détermination de la séquence
    int use_cw = open_cmd ^ invert_sens; 
    int *current_seq = (use_cw) ? seq_cw : seq_ccw;

    // 3. Animation Moteur
    for (int i = 0; i < CYCLES_REQUIRED; i++) {
        for (int step = 0; step < 4; step++) {
            set_motor_bits(current_seq[step]);
            usleep(STEP_DELAY);
        }
    }

    // 4. Finalisation
    set_motor_bits(0); // Couper le courant
    is_open = open_cmd;
    printf("[ID:%d] Mouvement termine. Etat: %s\n", barrier_id, is_open ? "OUVERT" : "FERME");
}

void on_message(struct mosquitto *m, void *userdata, const struct mosquitto_message *msg) {
    if (msg->payloadlen == 0) return;
    char *text = (char *)msg->payload;
    char *topic = msg->topic;

    printf("[MQTT ID:%d] Topic: %s | Payload: %s\n", barrier_id, topic, text);

    // 1. Configuration du SENS
    if (strstr(topic, "/sens") != NULL) {
        if (strncmp(text, "INVERSE", 7) == 0) {
            invert_sens = 1;
            printf("[ID:%d] Sens : INVERSE\n", barrier_id);
        } else {
            invert_sens = 0;
            printf("[ID:%d] Sens : NORMAL\n", barrier_id);
        }
    }
    // 2. Commande de MOUVEMENT (/state)
    else if (strstr(topic, "/state") != NULL) {
        if (strncmp(text, "OPEN", 4) == 0) {
            move_barrier(1);
        } 
        else if (strncmp(text, "CLOSE", 5) == 0) {
            move_barrier(0);
        }
    }
}

int main(int argc, char *argv[]) {
    // 0. RECUPERATION DE L'ARGUMENT (ID)
    if (argc < 2) {
        printf("Usage: %s <ID_BARRIERE>\n", argv[0]);
        printf("IDs disponibles :\n 0 (JA Haut)\n 1 (JA Bas)\n 2 (JB Haut)\n 3 (JB Bas)\n");
        return 1;
    }
    barrier_id = atoi(argv[1]);

    if (barrier_id < 0 || barrier_id > 3) {
        printf("Erreur : ID doit etre entre 0 et 3.\n");
        return 1;
    }

    // SELECTION ADRESSE DYNAMIQUE
    unsigned int target_addr = BARRIER_ADDRS[barrier_id];
    printf("--- DEMARRAGE BARRIERE %d (Addr: 0x%X) ---\n", barrier_id, target_addr);

    // 1. MAPPING MEMOIRE
    int mem_fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (mem_fd < 0) {
        perror("Erreur ouverture /dev/mem");
        return 1;
    }

    // Note : On map la page contenant l'adresse cible
    void *map_base = mmap(0, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, mem_fd, target_addr & ~0xFFF);
    if (map_base == MAP_FAILED) {
        perror("Erreur mmap");
        return 1;
    }
    
    // Pointeur final vers le registre exact
    motor_reg = (volatile unsigned int *)(map_base + (target_addr & 0xFFF));

    // 2. MQTT INIT
    mosquitto_lib_init();
    
    char client_id[30];
    sprintf(client_id, "barrier_client_%d", barrier_id);
    mosq = mosquitto_new(client_id, true, NULL);

    if (!mosq) return 1;
    mosquitto_message_callback_set(mosq, on_message);

    if (mosquitto_connect(mosq, BROKER_IP, BROKER_PORT, 60) != MOSQ_ERR_SUCCESS) {
        fprintf(stderr, "Erreur connexion broker (%s)\n", BROKER_IP);
        return 1;
    }

    // 3. ABONNEMENT
    char topic_state[50];
    char topic_sens[50];

    sprintf(topic_state, "%s_%d/state", BASE_TOPIC, barrier_id);
    sprintf(topic_sens, "%s_%d/sens", BASE_TOPIC, barrier_id);

    mosquitto_subscribe(mosq, NULL, topic_state, 0);
    mosquitto_subscribe(mosq, NULL, topic_sens, 0);

    printf("Pret. En attente de messages MQTT...\n");

    mosquitto_loop_forever(mosq, -1, 1);

    return 0;
}