#include "Stepper.h"
#include <Arduino.h>

const int STEP_SEQUENCES[8][4] = {
    {1, 0, 0, 0}, // Phase 0
    {1, 1, 0, 0}, // Phase 1
    {0, 1, 0, 0}, // Phase 2
    {0, 1, 1, 0}, // Phase 3
    {0, 0, 1, 0}, // Phase 4
    {0, 0, 1, 1}, // Phase 5
    {0, 0, 0, 1}, // Phase 6
    {1, 0, 0, 1}  // Phase 7
};

int RESOLUTION = 4096; // Default steps per revolution for 28BYJ-48
int NUM_PHASES = 8;
int STEP_DELAY = 10;

Stepper::Stepper(int p1, int p2, int p3, int p4) {
    pins[0] = p1;
    pins[1] = p2;
    pins[2] = p3;
    pins[3] = p4;
    currentStep = 0;
    stepPhase = 0;
}

void Stepper::step() {

    writePins(STEP_SEQUENCES[stepPhase]);
    // Keep step between 0-4095
    currentStep += 1;
    if (currentStep >= RESOLUTION - 1)
        currentStep = 0;

    // Keep phase between 0-7
    stepPhase += 1;
    if (stepPhase >= NUM_PHASES - 1)
        stepPhase = 0;
}

void Stepper::writePins(const int* signals) {
    // Replace with your specific platform's write function (e.g., digitalWrite)
    for (int i = 0; i < sizeof(4); i++)
    {
        digitalWrite(pins[i], signals[i]);
    }
    delay(STEP_DELAY);
}