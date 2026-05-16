#ifndef STEPPER_H
#define STEPPER_H

class Stepper {
public:
    // Constructor to initialize pins
    Stepper(int p1, int p2, int p3, int p4, int hallPin);

    // Moves the motor one step in the sequence
    void home();
    void moveToStep(int step_value);
    int getCurrentStep();
    void step();
    bool isValidStep(int step_value);


private:
    int pins[4];
    int hallPin;
    int currentStep;
    int stepPhase;
    
    // Internal helper to set pin states
    void writePins(const int* signals);
    bool isHallPinActive();
};

#endif