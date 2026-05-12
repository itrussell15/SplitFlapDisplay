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
        uint16_t incoming_data = ((uint16_t)incoming_buffer[4] << 8) | incoming_buffer[3];

        OutgoingMessage message;

        message.start_val = OUTGOING_START_BYTE;
        message.module_id = incoming_buffer[1];
        message.command_id = incoming_buffer[2];
        message.data_value = incoming_data;
        message.status = true;
        message.checksum = 249;
        message.end_val = OUTGOING_END_BYTE;
        
        Serial.write((byte*)&message, sizeof(message));
      }
    } else {
      Serial.read(); // Discard trash
    }
  }
}

int16_t convertBytesToInt16(byte data1, byte data2)
{
  
}
