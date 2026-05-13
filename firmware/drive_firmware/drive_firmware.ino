int INCOMING_SIZE = 7;
byte INCOMING_START_BYTE = 2;
byte INCOMING_END_BYTE = 3;

int OUTGOING_SIZE = 8; 
byte OUTGOING_START_BYTE = 4;
byte OUTGOING_END_BYTE = 5;

int MODULE_ID = 1;

struct __attribute__((__packed__)) OutgoingMessage {
  uint8_t  start_val;  // 1
  uint8_t  module_id;  // 1
  uint8_t  command_id; // 1
  int16_t  data_value; // 2
  uint8_t  status;     // 1
  uint8_t  checksum;   // 1 
  uint8_t  end_val;    // 1
}; // Total = 8 bytes

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

int motorSteps = 0;

void setup() {
  Serial.begin(9600);
  pinMode(LED_BUILTIN, OUTPUT);
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
        message.command_id = incoming_buffer[2];
        uint16_t data_value = convertBytesToInt16(incoming_buffer[3], incoming_buffer[4]);
        
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
  // TODO: Calculate checksum for outgoing message
  message.start_val = OUTGOING_START_BYTE;
  message.checksum = calculateOutgoingChecksum(message);
  message.end_val = OUTGOING_END_BYTE;
  Serial.write((byte*)&message, sizeof(message));
}

bool validateChecksum(byte* buffer) {
  uint8_t module_id = buffer[1];
  uint8_t command_id = buffer[2];
  uint16_t data_value = convertBytesToInt16(buffer[3], buffer[4]);
  uint8_t received_checksum = buffer[5];

  uint8_t calculated_checksum = calculateIncomingChecksum(module_id, command_id, data_value);
  return received_checksum == calculated_checksum;
}

int calculateIncomingChecksum(uint8_t module_id, uint8_t command_id, uint16_t data_value) {
  // Python Code
  // low_byte = data_value & 0xFF
  // high_byte = (data_value >> 8) & 0xFF
  // return module_id ^ command_value ^ low_byte ^ high_byte
  uint8_t low_byte = data_value & 0xFF;
  uint8_t high_byte = (data_value >> 8) & 0xFF;
  return module_id ^ command_id ^ low_byte ^ high_byte;
}

int calculateOutgoingChecksum(OutgoingMessage message) {
  uint8_t low_byte = message.data_value & 0xFF;
  uint8_t high_byte = (message.data_value >> 8) & 0xFF;
  return message.module_id ^ message.command_id ^ low_byte ^ high_byte ^ message.status;
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
