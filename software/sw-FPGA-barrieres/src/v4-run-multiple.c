#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <mosquitto.h>

// --- CONFIGURATION GENERALE ---
#define BROKER_IP    "192.168.78.2"
#define BROKER_PORT  1883
#define BASE_TOPIC   "parking/barrier"
#define MAX_BARRIERS 4

// --- CONFIGURATION ADRESSES ---
unsigned int ALL_ADDRS[] = {
    0xF0000000, // ID 0
    0xF0000800, // ID 1
    0xF0002000, // ID 2
    0xF0002800  // ID 3
};

// --- CALIBRAGE MOTEUR ---
#define CYCLES_REQUIRED 128
#define STEP_DELAY      2500 

typedef struct {
    int id;
    volatile unsigned int *reg;
    int is_open;                
    int invert_sens; // 0=Normal, 1=Inversé
} Barrier;

Barrier barriers[MAX_BARRIERS];
int active_count = 0;

int seq_cw[]  = {1, 2, 4, 8}; 
int seq_ccw[] = {8, 4, 2, 1};

void set_motor_bits(Barrier *b, int val) {
    if (b->reg) *(b->reg) = val;
}

void move_barrier(Barrier *b, int open_cmd) {
    if (open_cmd == b->is_open) {
        printf("[ID:%d] Deja position %s. Ignore.\n", b->id, open_cmd ? "OUVERT" : "FERME");
        return;
    }

    // Calcul du sens réel selon la configuration
    // Si invert_sens=0 : 1=Open(CW), 0=Close(CCW)
    // Si invert_sens=1 : 1=Open(CCW), 0=Close(CW)
    int use_cw = open_cmd ^ b->invert_sens; 

    printf("[ID:%d] Action : %s (Mode: %s -> Moteur: %s)\n", 
            b->id, 
            open_cmd ? "OUVERTURE" : "FERMETURE",
            b->invert_sens ? "INVERSE" : "NORMAL",
            use_cw ? "Sens A (CW)" : "Sens B (CCW)");

    int *current_seq = (use_cw) ? seq_cw : seq_ccw;

    for (int i = 0; i < CYCLES_REQUIRED; i++) {
        for (int step = 0; step < 4; step++) {
            set_motor_bits(b, current_seq[step]);
            usleep(STEP_DELAY);
        }
    }
    set_motor_bits(b, 0);
    b->is_open = open_cmd;
    printf("[ID:%d] Termine.\n", b->id);
}

void on_message(struct mosquitto *m, void *userdata, const struct mosquitto_message *msg) {
    if (msg->payloadlen == 0) return;
    char *text = (char *)msg->payload;
    char *topic = msg->topic;

    Barrier *target = NULL;
    for(int i = 0; i < active_count; i++) {
        char id_token[10];
        sprintf(id_token, "_%d/", barriers[i].id);
        if (strstr(topic, id_token) != NULL) {
            target = &barriers[i];
            break;
        }
    }

    if (target == NULL) return;

    printf("[MQTT ID:%d] Cmd: %s\n", target->id, text);

    if (strstr(topic, "/sens") != NULL) {
        // Mise à jour dynamique du sens
        target->invert_sens = (strncmp(text, "INVERSE", 7) == 0) ? 1 : 0;
        printf("[ID:%d] Sens MAJ par MQTT : %s\n", target->id, target->invert_sens ? "INVERSE" : "NORMAL");
    }
    else if (strstr(topic, "/state") != NULL) {
        if (strncmp(text, "OPEN", 4) == 0)       move_barrier(target, 1);
        else if (strncmp(text, "CLOSE", 5) == 0) move_barrier(target, 0);
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s <ID:SENS> <ID:SENS> ...\n", argv[0]);
        printf("   ID   : 0 a 3\n");
        printf("   SENS : 0=Normal, 1=Inverse\n");
        printf("Exemple: %s 0:1 1:0 (ID 0 inverse, ID 1 normal)\n", argv[0]);
        return 1;
    }

    printf("--- DEMARRAGE BARRIERES (CONFIG AVANCEE) ---\n");

    int mem_fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (mem_fd < 0) { perror("Erreur /dev/mem"); return 1; }

    // --- PARSING DES ARGUMENTS ---
    for (int i = 1; i < argc; i++) {
        if (active_count >= MAX_BARRIERS) break;

        char *arg_str = argv[i];
        int id = 0;
        int sens = 0;

        // Vérification de la présence du séparateur ':'
        char *colon_pos = strchr(arg_str, ':');
        
        if (colon_pos != NULL) {
            // Format "ID:SENS"
            *colon_pos = '\0'; // On coupe la chaine temporairement
            id = atoi(arg_str);
            sens = atoi(colon_pos + 1);
        } else {
            // Format "ID" simple (Sens par défaut = 0)
            id = atoi(arg_str);
            sens = 0;
        }

        if (id < 0 || id > 3) {
            printf("Erreur: ID %d invalide. Ignore.\n", id);
            continue;
        }

        // Configuration
        Barrier *b = &barriers[active_count];
        b->id = id;
        b->is_open = 0;
        b->invert_sens = (sens > 0) ? 1 : 0; // Force 0 ou 1

        unsigned int addr = ALL_ADDRS[id];
        void *map_base = mmap(0, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, mem_fd, addr & ~0xFFF);
        
        if (map_base == MAP_FAILED) {
            printf("Erreur mapping ID %d. Ignore.\n", id);
            continue;
        }
        b->reg = (volatile unsigned int *)(map_base + (addr & 0xFFF));

        printf("-> Barriere ID %d activee | Reg: %p | Sens Init: %s\n", 
               b->id, b->reg, b->invert_sens ? "INVERSE" : "NORMAL");
        
        active_count++;
    }

    if (active_count == 0) return 1;

    // --- MQTT SETUP ---
    mosquitto_lib_init();
    char client_id[50];
    sprintf(client_id, "barrier_v5_%d", getpid());
    struct mosquitto *mosq = mosquitto_new(client_id, true, NULL);

    if (!mosq) return 1;
    mosquitto_message_callback_set(mosq, on_message);

    if (mosquitto_connect(mosq, BROKER_IP, BROKER_PORT, 60) != MOSQ_ERR_SUCCESS) {
        fprintf(stderr, "Erreur broker\n");
        return 1;
    }

    for(int i = 0; i < active_count; i++) {
        char topic[64];
        sprintf(topic, "%s_%d/state", BASE_TOPIC, barriers[i].id);
        mosquitto_subscribe(mosq, NULL, topic, 0);
        sprintf(topic, "%s_%d/sens", BASE_TOPIC, barriers[i].id);
        mosquitto_subscribe(mosq, NULL, topic, 0);
    }

    printf("Pret. En attente...\n");
    mosquitto_loop_forever(mosq, -1, 1);

    return 0;
}