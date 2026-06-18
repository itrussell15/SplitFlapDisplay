#ifndef STEPPER_H
#define STEPPER_H

class Stepper {
public:
    // Constructor to initialize pins
    Stepper(int p1, int p2, int p3, int p4, int hallPin);

    // Moves the motor one step in the sequence
    void home(int home_offset);
    void moveToStep(int step_value);
    int getCurrentStep();
    void step();
    void setDirection(int direction);
    void reverseDirection();
    bool isValidStep(int step_value);
    void release();
    int get_max_steps();
    void set_max_steps(int value);
    int stepsToTarget(int target);  // forward-only distance from currentStep to target

    int currentStep;


private:
    int pins[4];
    int hallPin;
    int stepPhase;
    int stepDirection;
    int max_steps;

    // Re-Zeroing
    bool hallState;
    bool lastHallState;

    // Internal helper to set pin states
    void writePins(const int* signals);
    bool isHallPinActive();
};

#endif
