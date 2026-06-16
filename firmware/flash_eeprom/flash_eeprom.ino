#include <EEPROM.h>

// ########## EEPROM LOCATIONS ################
const int MODULE_ROW_LOCATION = 0;
const int MODULE_COLUMN_LOCATION = 1;
const int AUTO_HOME_LOCATION = 2;
const int HOME_OFFSET_VALUE_LOCATION = 3;
const int MAX_STEP_LOCATION = 5;
const int POSITION_VALUES_START_LOCATION = 100;
// ###########################################

// CHANGE THESE VALUES PER MODULE
const int MODULE_ROW = 1;
const int MODULE_COLUMN = 5;
const int HOME_OFFSET = 2000;
const bool AUTO_HOME = true;

// MODULE PROPERTIES
const int NUM_POSITIONS = 64;
const int MOTOR_RESOLUTION = 4096;
const int STATUS_LED_PIN = PIN_PA3;


void setup() {

  pinMode(STATUS_LED_PIN, OUTPUT);
  
  EEPROM.update(MODULE_ROW_LOCATION, MODULE_ROW);
  EEPROM.update(MODULE_COLUMN_LOCATION, MODULE_COLUMN);
  EEPROM.update(AUTO_HOME_LOCATION, AUTO_HOME);
  saveHomeOffset(HOME_OFFSET);
  saveMaxSteps(4096);
  
  // Set Positions;
  int evenStep = MOTOR_RESOLUTION / NUM_POSITIONS;
  for(int i = 0; i < NUM_POSITIONS; i++)
  {
    int value = (i * evenStep);
    value = value;
    saveStepperPosition(i, value);
  }

  for(int i=0; i<3; i++) {
    digitalWrite(STATUS_LED_PIN, HIGH); delay(500);
    digitalWrite(STATUS_LED_PIN, LOW);  delay(100);
  }
}

void loop() {}

void saveInt16ToEeprom(int address, uint16_t value)
{
    EEPROM.put(address, value); // Writes 2 bytes starting at 'address'
}

void saveMaxSteps(uint16_t stepValue) {
  saveInt16ToEeprom(MAX_STEP_LOCATION, stepValue);
}

void saveHomeOffset(uint16_t stepValue) {
  saveInt16ToEeprom(HOME_OFFSET_VALUE_LOCATION, stepValue);
}

// Save a position to a specific index (0-63)
void saveStepperPosition(int index, uint16_t stepValue) {
  index = constrain(index, 0, NUM_POSITIONS - 1);
  int address = POSITION_VALUES_START_LOCATION + (index * sizeof(uint16_t));
  saveInt16ToEeprom(address, stepValue);
}
