#include <EEPROM.h>

// ########## EEPROM LOCATIONS ################
const int MODULE_ROW_LOCATION = 0;
const int MODULE_COLUMN_LOCATION = 1;
const int AUTO_HOME_LOCATION = 2;
const int HOME_OFFSET_VALUE_LOCATION = 3;
const int MOTOR_NUM_STEPS_LOCATION = 5;
const int MAJOR_FIRMWARE_VERSION_LOCATION = 61;
const int MINOR_FIRMWARE_VERSION_LOCATION = 62;
const int POSITION_VALUES_START_LOCATION = 63;
// ###########################################

// CHANGE THESE VALUES PER MODULE
const int MODULE_ROW = 1;
const int MODULE_COLUMN = 1;
const int HOME_OFFSET = 1000;
const bool AUTO_HOME = true;
const int MAJOR_FIRMWARE_VERSION = 0
const int MINOR_FIRMWARE_VERSION = 1

// MODULE PROPERTIES
const int NUM_FLAPS = 64;
const int MOTOR_RESOLUTION = 4096;

void setup() {

  EEPROM.update(MODULE_ROW_LOCATION, MODULE_ROW);
  EEPROM.update(MODULE_COLUMN_LOCATION, MODULE_COLUMN);
  EEPROM.update(AUTO_HOME_LOCATION, AUTO_HOME);
  EEPROM.update(MAJOR_FIRMWARE_VERSION_LOCATION, MAJOR_FIRMWARE_VERSION);
  EEPROM.update(MINOR_FIRMWARE_VERSION_LOCATION, MINOR_FIRMWARE_VERSION);
  saveMotorNumSteps(MOTOR_RESOLUTION);
  saveHomeOffset(HOME_OFFSET);
  
  // Set Positions;
  int evenStep = MOTOR_RESOLUTION / NUM_FLAPS;
  for(int i = 0; i < NUM_FLAPS; i++)
  {
    int value = (i * evenStep);
    value = value % MOTOR_RESOLUTION;
    saveStepperPosition(i, value);
  }

  for(int i=0; i<3; i++) {
    digitalWrite(STATUS_LED_PIN, HIGH); delay(500);
    digitalWrite(STATUS_LED_PIN, LOW);  delay(100);
  }
}

void loop() {}

void saveInt16ToEeprom(int start_location, uint16_t value)
{
  // Shift to correct location
  int address = start_location * sizeof(uint16_t);
  EEPROM.put(address, value);
}

void saveHomeOffset(uint16_t stepValue) {
  saveInt16ToEeprom(HOME_OFFSET_VALUE_LOCATION, stepValue);
}

void saveMotorNumSteps(uint16_t stepValue) {
  saveInt16ToEeprom(MOTOR_NUM_STEPS_LOCATION, stepValue);
}

// Save a position to a specific index (0-63)
void saveStepperPosition(int index, uint16_t stepValue) {
  index = constrain(index, 0, NUM_POSITIONS - 1);
  int address = POSITION_VALUES_START_LOCATION + (index * sizeof(uint16_t));
  saveInt16ToEeprom(address, stepValue);
}
