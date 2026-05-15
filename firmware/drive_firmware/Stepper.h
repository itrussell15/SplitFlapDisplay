#ifndef STEPPER_H
#define STEPPER_H

class Stepper {
public:
    // Constructor to initialize pins
    Stepper(int p1, int p2, int p3, int p4);

    // Moves the motor one step in the sequence
    void step();

private:
    int pins[4];
    int currentStep;
    int stepPhase;
    
    // Internal helper to set pin states
    void writePins(const int* signals);
};

#endif