int INCOMING_SIZE = 7;
byte INCOMING_START_BYTE = 2;
byte INCOMING_END_BYTE = 3;

// Changed to 8 to match your data, or remove the 8th value
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

        // Combine 2 incoming data bytes into 1 value up to 4096
        // uint16_t incoming_data = ((uint16_t)incoming_buffer[4] << 8) | incoming_buffer[3];

        // Bad Checksum, send error response
        if (!validateChecksum(incoming_buffer))
        {
          OutgoingMessage message;
          // Populate the outgoing message fields with known values
          message.start_val = OUTGOING_START_BYTE;
          message.module_id = incoming_buffer[1];
          message.command_id = incoming_buffer[2];
          message.end_val = OUTGOING_END_BYTE;
          message.status = false;
          message.data_value = 1; // 1 for checksum error
          SendSerialResponse(message);
          continue;
        }
        
        OutgoingMessage message = handleIncomingMessage(
          incoming_buffer[1],
          incoming_buffer[2],
          convertBytesToInt16(incoming_buffer[3], incoming_buffer[4])
        );
        SendSerialResponse(message);
        if (message.status)
        {
          // TODO: Do action after responding
        }
        
      }
    } else {
      Serial.read(); // Discard trash
    }
  }
}

void SendSerialResponse(OutgoingMessage message) {
  // TODO: Calculate checksum for outgoing message

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
  
uint16_t convertBytesToInt16(byte data1, byte data2)
{
  return ((uint16_t)data2 << 8) | data1;
}

OutgoingMessage handleIncomingMessage(uint8_t module_id, uint8_t command_id, int16_t data_value)
{

  OutgoingMessage message;
  message.start_val = OUTGOING_START_BYTE;
  message.end_val = OUTGOING_END_BYTE;
  message.module_id = module_id;
  message.command_id = command_id;

  switch (command_id) {
    // PING
    case 0:
      Serial.println("one");
      break;
    // HOME
    case 1:
      Serial.println("two");
      break;
    // STOP
    case 2:
      Serial.println("two");
      break;
    // GET_POSITION
    case 3:
      Serial.println("two");
      break;
    // SET_POSITION
    case 4:
      Serial.println("two");
      break;
    // MOVE_TO_POSITION
    case 5:
      Serial.println("two");
      break;
    // GET_SPEED
    case 6:
      Serial.println("two");
      break;
    // SET_SPEED
    case 7:
      Serial.println("two");
      break;
    // GET_STEPS
    case 8:
      Serial.println("two");
      break;
    // MOVE_TO_STEP
    case 9:
      Serial.println("two");
      break;
    default:
      Serial.println("other");
      break;
  }
}