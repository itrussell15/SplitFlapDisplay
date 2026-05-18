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
int STEP_DELAY = 1;

int currentStep;

Stepper::Stepper(int p1, int p2, int p3, int p4, int hallPin) {
    pins[0] = p1;
    pins[1] = p2;
    pins[2] = p3;
    pins[3] = p4;
    this->hallPin = hallPin;
    currentStep = 0;
    stepPhase = 0;
    
    // Set as output
    pinMode(p1, OUTPUT);
    pinMode(p2, OUTPUT);
    pinMode(p3, OUTPUT); 
    pinMode(p4, OUTPUT);
    pinMode(hallPin, INPUT_PULLUP);
}

void Stepper::home() {
    while(!isHallPinActive())
    {
        this->step();
        delay(STEP_DELAY);
    }
    currentStep = 0;
}

void Stepper::moveToStep(int step_value) {
    if (!isValidStep(step_value)) return;
    
    while(getCurrentStep() != step_value)
    {
        this->step();
        delay(STEP_DELAY);
    }
}

int Stepper::getCurrentStep() {
    return this->currentStep;
}

void Stepper::step() {
    writePins(STEP_SEQUENCES[stepPhase]);
    this->currentStep = (currentStep + 1);
    this->stepPhase = (stepPhase + 1) % NUM_PHASES;
}

bool Stepper::isValidStep(int step_value)
{
  return step_value >= 0 && step_value <= RESOLUTION - 1;
}

void Stepper::writePins(const int* signals) {
    for (int i = 0; i < 4; i++)
    {
        digitalWrite(pins[i], signals[i]);
    }
}

bool Stepper::isHallPinActive() {
    return digitalRead(hallPin);
}
