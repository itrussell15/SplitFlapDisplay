#include <EEPROM.h>

// CHANGE THIS VALUE PER MODULE
const int MODULE_ID = 1;
const int NUM_FLAPS = 64;
const int MOTOR_RESOLUTION = 4096;
const int HOME_OFFSET = 0;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  // Set Module ID
 EEPROM.update(0, MODULE_ID); 
 Serial.print("Module ID: ");
 Serial.println(MODULE_ID);

  // Set Positions;
  int evenStep = MOTOR_RESOLUTION / NUM_FLAPS;
  for(int i = 0; i < NUM_FLAPS; i++)
  {
    int value = (i * evenStep) + HOME_OFFSET;
    value = value % MOTOR_RESOLUTION;
    saveStepperPosition(i, value);
    Serial.print("Position ");
    Serial.print(i);
    Serial.print(" set to ");
    Serial.println(value);
  }

  for(int i = 0; i < NUM_FLAPS; i++)
  {
    int value = getStepperPosition(i);
    Serial.print("Position ");
    Serial.print(i);
    Serial.print(" set to ");
    Serial.println(value);
  }
}

void loop() {}

void saveStepperPosition(int index, uint16_t stepValue) {
  index = constrain(index, 0, NUM_FLAPS - 1);
  // Shift 1 to reserve byte 0 for "Module ID"
  index += 1;
  int address = index * sizeof(uint16_t); // Each index is 2 bytes apart
  EEPROM.put(address, stepValue);
}

// Retrieve a position from EEPROM
uint16_t getStepperPosition(int index) {
  if (index >= 0 && index < NUM_FLAPS) {
      index += 1;
      uint16_t stepValue;
      EEPROM.get(index * sizeof(uint16_t), stepValue);
      return stepValue;
  }
  return 0; // Return 0 if index is out of bounds
}
