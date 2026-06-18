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

const int RELEASE_SEQUENCE[4] = {0, 0, 0, 0};


int NUM_PHASES = 8;
int STEP_DELAY = 1;

Stepper::Stepper(int p1, int p2, int p3, int p4, int hallPin) {
    pins[0] = p1;
    pins[1] = p2;
    pins[2] = p3;
    pins[3] = p4;
    this->hallPin = hallPin;
    currentStep = 0;
    stepPhase = 7;
    stepDirection = 1;
    this->max_steps = 4096;

    // Set as output
    pinMode(p1, OUTPUT);
    pinMode(p2, OUTPUT);
    pinMode(p3, OUTPUT);
    pinMode(p4, OUTPUT);
    pinMode(hallPin, INPUT_PULLUP);
}

void Stepper::setDirection(int direction) {
    this->stepDirection = direction >= 0 ? 1 : -1;
}

void Stepper::reverseDirection() {
    this->stepDirection = -this->stepDirection;
}

void Stepper::home(int home_offset = 0) {
    while(!isHallPinActive())
    {
        this->step();
        delay(STEP_DELAY);
    }

    delay(500);
    for (int i = 0; i < home_offset; i++)
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
    if (stepDirection > 0) {
        this->currentStep = (currentStep + 1) % this->max_steps;
        this->stepPhase = (stepPhase - 1 + NUM_PHASES) % NUM_PHASES;
    } else {
        this->currentStep = (currentStep - 1 + this->max_steps) % this->max_steps;
        this->stepPhase = (stepPhase + 1) % NUM_PHASES;
    }

    // Re-Zero if we hit the hall sensor
    hallState = isHallPinActive();
    if (hallState && !lastHallState)
        this->currentStep = 0;
    lastHallState = hallState;
}

void Stepper::release() {
    writePins(RELEASE_SEQUENCE);
}

bool Stepper::isValidStep(int step_value)
{
  return step_value >= 0 && step_value <= this->max_steps - 1;
}

void Stepper::writePins(const int* signals) {
    for (int i = 0; i < 4; i++)
    {
        digitalWrite(pins[i], signals[i]);
    }
}

bool Stepper::isHallPinActive() {
    return !digitalRead(hallPin);
}

int Stepper::get_max_steps()
{
  return this->max_steps;
}

void Stepper::set_max_steps(int value)
{
   this->max_steps = value;
}

// Number of steps the motor will travel to reach `target` from its current
// position. Moves are forward-only and wrap at max_steps, so this is the
// forward delta (0 .. max_steps-1). Use it to decide if a move is "small".
int Stepper::stepsToTarget(int target)
{
  int delta = (target - this->currentStep) % this->max_steps;
  if (delta < 0)
    delta += this->max_steps;
  return delta;
}
