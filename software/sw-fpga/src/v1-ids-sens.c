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
#define MOTOR_ADDR   0xF0000000

// --- CALIBRAGE MOTEUR ---
#define CYCLES_REQUIRED 128
#define STEP_DELAY      2500 

// Variables Globales
volatile unsigned int *motor_reg = NULL;
struct mosquitto *mosq = NULL;

// Etat de la barrière
int barrier_id = 0;      // ID de la barrière (0, 1, 2...)
int is_open = 0;         // 0 = Fermée, 1 = Ouverte
int invert_sens = 0;     // 0 = Normal (Gauche), 1 = Inversé (Droite)

// Séquences physiques
int seq_cw[]  = {1, 2, 4, 8}; // Clockwise (Sens A)
int seq_ccw[] = {8, 4, 2, 1}; // Counter-Clockwise (Sens B)

void set_motor_bits(int val) {
    if (motor_reg) *motor_reg = val;
}

// Fonction de mouvement
// open_cmd : 1 = OUVRIR, 0 = FERMER
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
    // Logique :
    // - Si Normal : Ouvrir = CW, Fermer = CCW
    // - Si Inversé : Ouvrir = CCW, Fermer = CW
    // On utilise un XOR (^) pour simplifier la logique
    int use_cw = open_cmd ^ invert_sens; 
    
    // Note : Si open_cmd=1 et invert=0 -> use_cw=1 (Vrai) -> On ouvre en CW
    // Note : Si open_cmd=1 et invert=1 -> use_cw=0 (Faux) -> On ouvre en CCW

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

    // ANALYSE DU TOPIC (Est-ce /state ou /sens ?)
    
    // 1. Configuration du SENS
    if (strstr(topic, "/sens") != NULL) {
        if (strncmp(text, "INVERSE", 7) == 0) {
            invert_sens = 1;
            printf("[CONFIG] Sens d'ouverture : INVERSE (Pour montage Droite)\n");
        } else {
            invert_sens = 0;
            printf("[CONFIG] Sens d'ouverture : NORMAL (Pour montage Gauche)\n");
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
        printf("Usage: %s <ID_BARRIERE>\nExample: %s 0\n", argv[0], argv[0]);
        return 1;
    }
    barrier_id = atoi(argv[1]);

    // 1. MAPPING MEMOIRE
    int mem_fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (mem_fd < 0) return 1;
    void *map_base = mmap(0, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, mem_fd, MOTOR_ADDR & ~0xFFF);
    if (map_base == MAP_FAILED) return 1;
    motor_reg = (volatile unsigned int *)(map_base + (MOTOR_ADDR & 0xFFF));

    // 2. MQTT INIT
    mosquitto_lib_init();
    
    // Nom unique du client : barrier_client_0, barrier_client_1...
    char client_id[30];
    sprintf(client_id, "barrier_client_%d", barrier_id);
    mosq = mosquitto_new(client_id, true, NULL);

    if (!mosq) return 1;
    mosquitto_message_callback_set(mosq, on_message);

    if (mosquitto_connect(mosq, BROKER_IP, BROKER_PORT, 60) != MOSQ_ERR_SUCCESS) {
        fprintf(stderr, "Erreur connexion broker.\n");
        return 1;
    }

    // 3. CONSTRUCTION DES TOPICS ET ABONNEMENT
    char topic_state[50];
    char topic_sens[50];

    // Crée: parking/barrier_0/state
    sprintf(topic_state, "%s_%d/state", BASE_TOPIC, barrier_id);
    // Crée: parking/barrier_0/sens
    sprintf(topic_sens, "%s_%d/sens", BASE_TOPIC, barrier_id);

    mosquitto_subscribe(mosq, NULL, topic_state, 0);
    mosquitto_subscribe(mosq, NULL, topic_sens, 0);

    printf("=== BARRIERE %d DEMARREE ===\n", barrier_id);
    printf("Topics ecoutes :\n  - %s\n  - %s\n", topic_state, topic_sens);
    printf("Sens par defaut : NORMAL\n");

    mosquitto_loop_forever(mosq, -1, 1);

    return 0;
}