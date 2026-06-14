#include <SoftwareSerial.h>
#include <EEPROM.h>
#include "Stepper.h"

// ##### PIN DEFINITIONS #####
const int RS485_RX = 3;
const int RS485_TX = 1;
const int RS485_DE = 2;
const int SERIAL_DELAY_MS = 50;

SoftwareSerial rs485(RS485_RX, RS485_TX);

const int HALL_PIN = 4;
const int IN4 = 6;
const int IN3 = 7;
const int IN2 = 8;
const int IN1 = 9;
const int STATUS_LED_PIN = PIN_PA3;
// ##########################

// ########## EEPROM LOCATIONS ################
const int MODULE_ROW_LOCATION = 0;
const int MODULE_COLUMN_LOCATION = 1;
const int AUTO_HOME_LOCATION = 2;
const int HOME_OFFSET_VALUE_LOCATION = 3;
const int POSITION_VALUES_START_LOCATION = 5;
// ###########################################

const int INCOMING_SIZE = 9;
const byte INCOMING_START_BYTE = 2;
const byte INCOMING_END_BYTE = 3;

const byte OUTGOING_START_BYTE = 4;
const byte OUTGOING_END_BYTE = 5;

struct __attribute__((__packed__)) IncomingMessage {
  uint8_t  start_val;  // 1
  uint8_t  row;  // 1
  uint8_t  column;  // 1
  uint8_t  sequence_id;// 1
  uint8_t  command_id; // 1
  uint16_t  data_value; // 2
  uint8_t  checksum;   // 1 
  uint8_t  end_val;    // 1
}; // Total = 9 bytes

struct __attribute__((__packed__)) OutgoingMessage {
  uint8_t  start_val;  // 1
  uint8_t  row;  // 1
  uint8_t  column;  // 1
  uint8_t  sequence_id;// 1
  uint8_t  command_id; // 1
  int16_t  data_value; // 2
  uint8_t  status;     // 1
  uint8_t  checksum;   // 1 
  uint8_t  end_val;    // 1
}; // Total = 10 bytes

enum ErrorCode {
  ERROR_BAD_CHECKSUM = 1,
  ERROR_COMMAND_NOT_FOUND = 2,
  ERROR_INVALID_POSITION = 3,
  ERROR_INVALID_STEP = 4
  ERROR_INVALID_VALUE = 5
};

enum Command {
  CMD_PING = 0,
  CMD_HOME = 1,
  CMD_STOP = 2,
  CMD_GET_POSITION = 3,
  CMD_SET_POSITION = 4,
  CMD_MOVE_TO_POSITION = 5,
  CMD_GET_SPEED = 6,
  CMD_SET_SPEED = 7,
  CMD_GET_STEPS = 8,
  CMD_MOVE_TO_STEP = 9,
  CMD_MOVE_REL_STEPS = 10,
  CMD_SET_STEP_TARGET = 11,
  CMD_SET_POSITION_TARGET = 12,
  CMD_MOVE_TO_TARGET = 13,
  CMD_HALL_EFFECT_STATUS = 14,
  CMD_IS_MOVING = 15,
  CMD_MOTOR_NUM_STEPS = 16,
  CMD_SET_HOME_OFFSET = 17
  CMD_SET_AUTO_HOME = 18,
  CMD_GET_EEPROM_VALUE = 19,
};

uint8_t MODULE_ROW;
uint8_t MODULE_COLUMN;
uint16_t HOME_OFFSET;
bool AUTO_HOME = true;
const int BAUDRATE = 9600;

// ##### MOTOR VALUES #####
// Locating
const int NUM_POSITIONS = 64;
const int MOTOR_RESOLUTION = 4096;
Stepper motor(IN1, IN2, IN3, IN4, HALL_PIN); 
int targetStep;
int cachedTargetStep;

// Timing
unsigned long previousStepMicros = 0;
const unsigned long STEP_INTERVAL_MICROS = 2000;
// ########################

void setup() {

  rs485.begin(BAUDRATE);

  // Pull from EEPROM;
  MODULE_ROW = getModuleRow();
  MODULE_COLUMN = getModuleColumn();
  HOME_OFFSET = getHomeOffset();
  AUTO_HOME = getAutoHome();

  // SERIAL COMMS
  pinMode(RS485_DE, OUTPUT);
  digitalWrite(RS485_DE, LOW);

  // Status Light
  pinMode(STATUS_LED_PIN, OUTPUT);
  for(int i=0; i<5; i++) {
    digitalWrite(STATUS_LED_PIN, HIGH); delay(100);
    digitalWrite(STATUS_LED_PIN, LOW);  delay(100);
  }
  previousStepMicros = micros();

  if (AUTO_HOME)
    motor.home();
  
}

void loop() {


  // Asynchronously to move to target
  if (targetStep != motor.getCurrentStep())
    moveMotorToTarget();
  else
  {
    motor.release();
  }

  if (!digitalRead(HALL_PIN))
  {
    digitalWrite(STATUS_LED_PIN, HIGH);
  }
  else
  {
    digitalWrite(STATUS_LED_PIN, LOW);
  }

  // Drain and frame incoming bytes. Self-resyncing so a stray start byte (0x02)
  // embedded in another module's reply -- notably column 2's address byte -- can
  // no longer eat the command that follows it on the shared bus.
  ParseIncomingSerial();
}

// Incrementally read the RS485 bus one byte at a time, syncing on the start byte
// and validating the end byte before acting on a frame. Every module hears every
// other module's replies, and those replies can contain 0x02 as a payload byte
// (e.g. the column field of module 2). The previous parser trusted any 0x02 and
// read a full 9-byte frame, swallowing the real start byte of the next command
// and silently dropping it. Here a mis-framed candidate fails the end-byte check
// and we resync by a single byte, so a command packed right behind the noise is
// recovered instead of lost.
void ParseIncomingSerial() {
  static byte frame[INCOMING_SIZE];
  static uint8_t frame_len = 0;

  while (rs485.available() > 0) {
    byte b = rs485.read();

    if (frame_len == 0) {
      // Hunting for a start byte; ignore replies and line noise.
      if (b == INCOMING_START_BYTE)
        frame[frame_len++] = b;
      continue;
    }

    frame[frame_len++] = b;
    if (frame_len < INCOMING_SIZE)
      continue;

    if (frame[INCOMING_SIZE - 1] == INCOMING_END_BYTE) {
      processIncomingMessage(frame);
      frame_len = 0;
    } else {
      // False start byte: drop it and re-scan the bytes we already buffered for
      // the next start byte, so a real frame behind it isn't discarded too.
      uint8_t i = 1;
      while (i < frame_len && frame[i] != INCOMING_START_BYTE)
        i++;
      frame_len -= i;
      for (uint8_t j = 0; j < frame_len; j++)
        frame[j] = frame[j + i];
    }
  }
}

void processIncomingMessage(byte* incoming_buffer) {
  int row = incoming_buffer[1];
  int column = incoming_buffer[2];

  bool isTargetedMessage = isThisModule(row, column);
  bool isBroadcastMessage = isBroadcast(row, column);
  if (!isBroadcastMessage && !isTargetedMessage)
    return;

  OutgoingMessage message;
  message.row = MODULE_ROW;
  message.column = MODULE_COLUMN;
  message.sequence_id = incoming_buffer[3];
  message.command_id = incoming_buffer[4];
  uint16_t data_value = convertBytesToInt16(incoming_buffer[5], incoming_buffer[6]);

  // Only validate checksum if its a targeted message
  if (!validateChecksum(incoming_buffer) && isTargetedMessage) {
    message.data_value = ErrorCode::ERROR_BAD_CHECKSUM;
    message.status = false;
    SendSerialResponse(message);
    return;
  }
  message = handleIncomingMessage(message, data_value);

  // Only respond to targeted messages
  if (isTargetedMessage) {
    SendSerialResponse(message);
    performMessageAction(message);
  }

  if (isBroadcastMessage)
    doBroadcastResponse(message);
}

OutgoingMessage handleIncomingMessage(OutgoingMessage message, int16_t data_value)
{
  int step_value;
  Command command = (Command)message.command_id;
  switch (command) {
    case Command::CMD_PING:
      message.data_value = 0;
      message.status = true;
      break;
    case Command::CMD_HOME:
      // May need to respond and then move
      message.status = true;
      break;
    case Command::CMD_STOP:
      message.data_value = 2;
      message.status = true;
      break;
    case Command::CMD_GET_POSITION:
      // Returns the steps for a given position
      if (!isValidPosition(data_value))
      {
        message.data_value = ErrorCode::ERROR_INVALID_POSITION;
        message.status = false;
        break;
      }
      message.data_value = getStepperPosition(data_value);
      message.status = true;
      break;
    case Command::CMD_SET_POSITION:
      // Sets the position to be the current steps
      if (!isValidPosition(data_value))
      {
        message.data_value = ErrorCode::ERROR_INVALID_POSITION;
        message.status = false;
        break;
      } 
      step_value = motor.getCurrentStep();
      saveStepperPosition(data_value, step_value);
      message.data_value = 4;
      message.status = true;
      break;
    case Command::CMD_MOVE_TO_POSITION:
      if (!isValidPosition(data_value))
      {
        message.data_value = ErrorCode::ERROR_INVALID_POSITION;
        message.status = false;
        break;
      }
      step_value = getStepperPosition(data_value);
      message.data_value = step_value;
      message.status = true;
      break;
    case Command::CMD_GET_SPEED:
      message.data_value = 6;
      message.status = true;
      break;
    case Command::CMD_SET_SPEED:
      message.data_value = 7;
      message.status = true;
      break;
    case Command::CMD_GET_STEPS:
      message.data_value = motor.getCurrentStep();
      message.status = true;
      break;
    case Command::CMD_MOVE_TO_STEP:
      if (!motor.isValidStep(data_value))
      {
        message.data_value = ErrorCode::ERROR_INVALID_STEP;
        message.status = false;
        break;
      }
      targetStep = data_value;
      message.data_value = motor.getCurrentStep();
      message.status = true;
      break;
    case Command::CMD_SET_STEP_TARGET:
      if (!motor.isValidStep(data_value))
      {
        message.data_value = ErrorCode::ERROR_INVALID_STEP;
        message.status = false;
        break;
      }
      cachedTargetStep = data_value;
      message.data_value = cachedTargetStep;
      message.status = true;
      break;
    case Command::CMD_SET_POSITION_TARGET:
      if (!isValidPosition(data_value))
      {
        message.data_value = ErrorCode::ERROR_INVALID_POSITION;
        message.status = false;
        break;
      }
      cachedTargetStep = getStepperPosition(data_value);
      message.data_value = cachedTargetStep;
      message.status = true;
      break;
    case Command::CMD_MOVE_TO_TARGET:
      targetStep = cachedTargetStep;
      message.data_value = targetStep;
      message.status = true;
      break;
    case Command::CMD_HALL_EFFECT_STATUS:
      message.data_value = (int)!digitalRead(HALL_PIN);
      message.status = true;
      break;
    case Command::CMD_IS_MOVING:
      message.data_value = (int)isMoving();
      message.status = true;
      break;
    case Command::CMD_MOTOR_NUM_STEPS:
      // Test to determine the number of steps it takes to return to the hall sensor. ie a full rotation
      motor.home();
      delay(500);

      int step_count = 0;
      
      // Move until off hall sensor
      while (isHallPinActive())
      {
        motor.step();
        step_count += 1;
        delay(1);
      }

      // Move until back on to hall sensor
      while (!isHallPinActive())
      {
        motor.step();
        step_count += 1;
        delay(1);
      }
      message.status = true;
      message.data_value = step_count;
      break;
    case Command::CMD_SET_HOME_OFFSET:
      if (!motor.isValidStep(data_value))
      {
        message.data_value = ErrorCode::ERROR_INVALID_STEP;
        message.status = false;
        break;
      }
      message.data_value = data_value
      message.status = true;
      saveHomeOffset(data_value);
      HOME_OFFSET = data_value;
      break;
    case Command::CMD_SET_AUTO_HOME:
      if (data_value != 0 || data_value != 1)
      {
        message.data_value = ErrorCode::ERROR_INVALID_VALUE;
        message.status = false;
        break;
      }
      message.data_value = data_value
      message.status = true;
      setAutoHome(data_value);
    case Command::CMD_GET_EEPROM_VALUE:
      if (data_value < 0 || data_value > 256)
      {
        message.data_value = ErrorCode::ERROR_INVALID_EEPROM_LOCATION;
        message.status = false;
        break;
      }
      uint8_t value;
      EEPROM.get(AUTO_HOME_LOCATION, value);
      message.data_value = value;
      message.status = true;
      break;
    default:
      message.data_value = ErrorCode::ERROR_COMMAND_NOT_FOUND;
      message.status = false;
      break;
  }
  return message;
}

void SendSerialResponse(OutgoingMessage message) {
  message.start_val = OUTGOING_START_BYTE;
  message.checksum = calculateOutgoingChecksum(message);
  message.end_val = OUTGOING_END_BYTE;

  // TODO: Play with the timing for all these delays
  //delay(5);                    // Give host USB dongle time to switch to receive mode
  digitalWrite(RS485_DE, HIGH);
  delay(5);                    // Let RS485 transceiver stabilize before sending

  rs485.write((byte*)&message, sizeof(message));
  delay(5);
  digitalWrite(RS485_DE, LOW);
}

void performMessageAction(OutgoingMessage message)
{
  Command command = (Command)message.command_id;
  switch (command) {
    case Command::CMD_HOME:
      // Home
      motor.home(HOME_OFFSET);
      targetStep = motor.getCurrentStep();
      break;
    case Command::CMD_MOTOR_NUM_STEPS:
      // Home
      motor.home();
      delay(500);

      // Move to offset
      while (int i = 0; ; i < HOME_OFFSET; i++)
      {
        motor.step();
        delay(1);
      }

      // Set offset position to 0 and stay at that position
      motor.currentStep = 0;
      targetStep = motor.getCurrentStep();
      break;
    default:
      message.data_value = ErrorCode::ERROR_COMMAND_NOT_FOUND;
      message.status = false;
      break;
  }
  
}

void doBroadcastResponse(OutgoingMessage message)
{
  // Turn LED on if bad status
  if (!message.status)
  {
    digitalWrite(STATUS_LED_PIN, HIGH);
  }
}

void moveMotorToTarget()
{
  unsigned long currentMicros = micros();
  bool shouldStep = currentMicros - previousStepMicros >= STEP_INTERVAL_MICROS;
  if (shouldStep) {
    motor.step();
    previousStepMicros = currentMicros;
  }
}


bool validateChecksum(byte* buffer) {
  uint8_t row = buffer[1];
  uint8_t column = buffer[2];
  uint8_t sequence_id = buffer[3];
  uint8_t command_id = buffer[4];
  uint16_t data_value = convertBytesToInt16(buffer[5], buffer[6]);
  uint8_t received_checksum = buffer[7];

  uint8_t calculated_checksum = calculateIncomingChecksum(row, column, command_id, data_value, sequence_id);
  return received_checksum == calculated_checksum;
}

int calculateIncomingChecksum(uint8_t row, uint8_t column, uint8_t command_id, uint16_t data_value, uint8_t sequence_id) {
  uint8_t low_byte = data_value & 0xFF;
  uint8_t high_byte = (data_value >> 8) & 0xFF;
  return row ^ column ^ command_id ^ sequence_id ^ low_byte ^ high_byte;
}

int calculateOutgoingChecksum(OutgoingMessage message) {
  uint8_t low_byte = message.data_value & 0xFF;
  uint8_t high_byte = (message.data_value >> 8) & 0xFF;
  return message.row ^ message.column ^ message.command_id ^ low_byte ^ high_byte ^ message.status ^ message.sequence_id;
}

uint16_t convertBytesToInt16(byte data1, byte data2)
{
  return ((uint16_t)data2 << 8) | data1;
}

bool isValidPosition(int position)
{
  return position >= 0 && position <= NUM_POSITIONS - 1;
}

bool isThisModule(uint8_t row, uint8_t column) {
  return row == MODULE_ROW && column == MODULE_COLUMN;
}

bool isBroadcast(uint8_t row, uint8_t column) {
  return row == 0 && column == 0;
}

bool isMoving() {
  return motor.getCurrentStep() != targetStep;
}

uint8_t getModuleRow() {
  // Pulls the module row from EEPROM address 0. 
  // Should be between 0-255
  uint8_t id;
  EEPROM.get(MODULE_ROW_LOCATION, id);
  return id;
}

uint8_t getModuleColumn() { 
  // Should be between 0-255
  uint8_t id;
  EEPROM.get(MODULE_COLUMN_LOCATION, id);
  return id;
}

bool getAutoHome() { 
  bool value;
  EEPROM.get(AUTO_HOME_LOCATION, value);
  return (bool)value;
}

void setAutoHome(bool value) {
  EEPROM.put(AUTO_HOME_LOCATION, value);
}

uint16_t getInt16FromEeprom(int address)
{
    uint16_t value;
    EEPROM.get(address, value); // Reads 2 bytes starting at 'address'
    return value;
}

uint16_t getInt16FromEeprom(int address)
{
    uint16_t value;
    EEPROM.get(address, value); // Reads 2 bytes starting at 'address'
    return value;
}

uint16_t getHomeOffset() { 
  return getInt16FromEeprom(HOME_OFFSET_VALUE_LOCATION);
}

// Retrieve a position from EEPROM
uint16_t getStepperPosition(int index) {
  if (index >= 0 && index < NUM_POSITIONS) {
      // Calculate byte address: Start + (index * 2 bytes per int)
      int address = POSITION_VALUES_START_LOCATION + (index * sizeof(uint16_t));
      return getInt16FromEeprom(address);
  }
  return 0;
}

void saveInt16ToEeprom(int address, uint16_t value)
{
    EEPROM.put(address, value); // Writes 2 bytes starting at 'address'
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