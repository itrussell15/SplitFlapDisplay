#include <EEPROM.h>

// CHANGE THIS VALUE PER MODULE
const int MODULE_ROW = 0;
const int MODULE_COLUMN = 0;
const int NUM_FLAPS = 64;
const int MOTOR_RESOLUTION = 4096;
const int HOME_OFFSET = 0;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  // Set Module ID
 EEPROM.update(0, MODULE_ROW);
 EEPROM.update(1, MODULE_COLUMN); 
 Serial.print("Module row: ");
 Serial.print(MODULE_ROW);
 Serial.print("Module column: ");
 Serial.println(MODULE_COLUMN);
 Serial.println();

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
  // Shift 2 to reserve byte 0 and 1 for ROW and COLUMN
  index += 2;
  int address = index * sizeof(uint16_t); // Each index is 2 bytes apart
  EEPROM.put(address, stepValue);
}

// Retrieve a position from EEPROM
uint16_t getStepperPosition(int index) {
  if (index >= 0 && index < NUM_FLAPS) {
      // Shift 2 to reserve byte 0 and 1 for ROW and COLUMN
      index += 2;
      uint16_t stepValue;
      EEPROM.get(index * sizeof(uint16_t), stepValue);
      return stepValue;
  }
  return 0; // Return 0 if index is out of bounds
}
