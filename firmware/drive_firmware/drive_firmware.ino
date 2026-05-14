#include <EEPROM.h>

// ##### PIN DEFINITIONS #####
const int RS485_RX = 3;
const int RS485_TX = 1;
const int RS485_DE = 2;
const int SERIAL_DELAY_MS = 50;

const int HALL_PIN = 4;
const int IN4 = 6;
const int IN3 = 7;
const int IN2 = 8;
const int IN1 = 9;
// ##########################

const int INCOMING_SIZE = 8;
const byte INCOMING_START_BYTE = 2;
const byte INCOMING_END_BYTE = 3;

const byte OUTGOING_START_BYTE = 4;
const byte OUTGOING_END_BYTE = 5;

struct __attribute__((__packed__)) IncomingMessage {
  uint8_t  start_val;  // 1
  uint8_t  module_id;  // 1
  uint8_t  sequence_id;// 1
  uint8_t  command_id; // 1
  int16_t  data_value; // 2
  uint8_t  checksum;   // 1 
  uint8_t  end_val;    // 1
}; // Total = 8 bytes

// TODO: Add sequence number for more robust comms
struct __attribute__((__packed__)) OutgoingMessage {
  uint8_t  start_val;  // 1
  uint8_t  module_id;  // 1
  uint8_t  sequence_id;// 1
  uint8_t  command_id; // 1
  int16_t  data_value; // 2
  uint8_t  status;     // 1
  uint8_t  checksum;   // 1 
  uint8_t  end_val;    // 1
}; // Total = 9 bytes

enum ErrorCode {
  ERROR_BAD_CHECKSUM = 1,
  ERROR_COMMAND_NOT_FOUND = 2
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
  CMD_MOVE_TO_STEP = 9
};

const int MODULE_ID = 1;
const int BAUDRATE = 9600;

// ##### MOTOR VALUES #####
const int NUM_POSITIONS = 64;
int motorSteps = 0;
// ########################

void setup() {

  // TODO: Convert to RS485
  Serial.begin(BAUDRATE);

  // TODO: Pull ID from EEPROM
  // const int MODULE_ID = getModuleId();
  const int MODULE_ID = 1;
  
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(HALL_PIN, INPUT_PULLUP);

  // MOTOR DRIVER PINS
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); 
  pinMode(IN4, OUTPUT);

  // SERIAL COMMS
  pinMode(RS485_DE, OUTPUT);
  digitalWrite(RS485_DE, LOW); 
}

void loop() {
  
  if (Serial.available() >= INCOMING_SIZE) {
    if (Serial.peek() == INCOMING_START_BYTE) {
      byte incoming_buffer[INCOMING_SIZE];
      Serial.readBytes(incoming_buffer, INCOMING_SIZE);
      
      // Verify End Byte and Module ID
      if (incoming_buffer[INCOMING_SIZE - 1] == INCOMING_END_BYTE && incoming_buffer[1] == MODULE_ID) {
        OutgoingMessage message;
        
        message.module_id = incoming_buffer[1];
        message.sequence_id = incoming_buffer[2];
        message.command_id = incoming_buffer[3];
        uint16_t data_value = convertBytesToInt16(incoming_buffer[4], incoming_buffer[5]);
        
        if (!validateChecksum(incoming_buffer)){
          message.data_value = ErrorCode::ERROR_BAD_CHECKSUM;
          message.status = false;
          SendSerialResponse(message);
          return;
        }
        message = handleIncomingMessage(message, data_value);
        SendSerialResponse(message);
      }
    } else {
      Serial.read(); // Discard trash
    }
  }
}

void SendSerialResponse(OutgoingMessage message) {
  digitalWrite(RS485_DE, HIGH); // Start transmission
  message.start_val = OUTGOING_START_BYTE;
  message.checksum = calculateOutgoingChecksum(message);
  message.end_val = OUTGOING_END_BYTE;
  Serial.write((byte*)&message, sizeof(message));
  Serial.flush();
  delay(SERIAL_DELAY_MS);
  digitalWrite(RS485_DE, LOW); // End transmission
}

bool validateChecksum(byte* buffer) {
  uint8_t module_id = buffer[1];
  uint8_t sequence_id = buffer[2];
  uint8_t command_id = buffer[3];
  uint16_t data_value = convertBytesToInt16(buffer[4], buffer[5]);
  uint8_t received_checksum = buffer[6];

  uint8_t calculated_checksum = calculateIncomingChecksum(module_id, command_id, data_value, sequence_id);
  return received_checksum == calculated_checksum;
}

int calculateIncomingChecksum(uint8_t module_id, uint8_t command_id, uint16_t data_value, uint8_t sequence_id) {
  uint8_t low_byte = data_value & 0xFF;
  uint8_t high_byte = (data_value >> 8) & 0xFF;
  return module_id ^ command_id ^ sequence_id ^ low_byte ^ high_byte;
}

int calculateOutgoingChecksum(OutgoingMessage message) {
  uint8_t low_byte = message.data_value & 0xFF;
  uint8_t high_byte = (message.data_value >> 8) & 0xFF;
  return message.module_id ^ message.command_id ^ low_byte ^ high_byte ^ message.status ^ message.sequence_id;
}

uint16_t convertBytesToInt16(byte data1, byte data2)
{
  return ((uint16_t)data2 << 8) | data1;
}

OutgoingMessage handleIncomingMessage(OutgoingMessage message, int16_t data_value)
{
  Command command = (Command)message.command_id;
  switch (command) {
    case Command::CMD_PING:
      message.data_value = 0;
      message.status = true;
      break;
    case Command::CMD_HOME:
      message.data_value = 1;
      message.status = true;
      break;
    case Command::CMD_STOP:
      message.data_value = 2;
      message.status = true;
      break;
    case Command::CMD_GET_POSITION:
      message.data_value = 3;
      message.status = true;
      break;
    case Command::CMD_SET_POSITION:
      message.data_value = 4;
      message.status = true;
      break;
    case Command::CMD_MOVE_TO_POSITION:
      message.data_value = 5;
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
      message.data_value = motorSteps;
      message.status = true;
      break;
    case Command::CMD_MOVE_TO_STEP:
      motorSteps = data_value;
      message.data_value = motorSteps;
      message.status = true;
      break;
    default:
      message.data_value = ErrorCode::ERROR_COMMAND_NOT_FOUND;
      message.status = false;
      break;
  }
  return message;
}

uint8_t getModuleId() {
  // Pulls the module ID from EEPROM address 0. 
  // Should be between 0-255
  int id;
  EEPROM.get(0, id);
  return id;
}

// Save a position (0-4096) to a specific index (0-63)
void saveStepperPosition(int index, uint16_t stepValue) {
  // Shift 1 to reserve 0 for "Module ID"
  index += 1;
  index = constrain(index, 0, NUM_POSITIONS - 1);
  if (index >= 0 && index < NUM_POSITIONS) {
      int address = index * sizeof(uint16_t); // Each index is 2 bytes apart
      EEPROM.update(address, stepValue); 
  }
}

// Retrieve a position from EEPROM
uint16_t getStepperPosition(int index) {
  // Shift 1 to reserve 0 for "Module ID"
  index += 1;
  if (index >= 0 && index < NUM_POSITIONS) {
      uint16_t stepValue;
      EEPROM.get(index * sizeof(uint16_t), stepValue);
      return stepValue;
  }
  return 0; // Return 0 if index is out of bounds
}
