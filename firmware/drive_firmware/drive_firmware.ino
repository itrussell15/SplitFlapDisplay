int INCOMING_SIZE = 7;
byte INCOMING_START_BYTE = 2;
byte INCOMING_END_BYTE = 3;

// Changed to 8 to match your data, or remove the 8th value
int OUTGOING_SIZE = 8; 
byte OUTGOING_START_BYTE = 4;
byte OUTGOING_END_BYTE = 5;

byte MODULE_ID = 1;

struct __attribute__((__packed__)) OutgoingMessage {
  uint8_t  start_val;  // 1
  uint8_t  module_id;  // 1
  uint8_t  command_id; // 1
  int16_t  data_value; // 2
  uint8_t  status;     // 1 (using uint8_t instead of bool is safer for cross-platform)
  uint8_t  checksum;   // 1 (Changed from int16_t to uint8_t)
  uint8_t  end_val;    // 1
}; // Total = 8 bytes

void setup() {
  Serial.begin(9600);
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  // Define the buffer correctly  
  byte outgoing_buffer[OUTGOING_SIZE] = {OUTGOING_START_BYTE, MODULE_ID, 0x01, 0x01, 0x04, 0x01, 0x01, OUTGOING_END_BYTE};
  
  if (Serial.available() >= INCOMING_SIZE) {
    if (Serial.peek() == INCOMING_START_BYTE) {
      byte incoming_buffer[INCOMING_SIZE];
      Serial.readBytes(incoming_buffer, INCOMING_SIZE);
      
      // Verify End Byte and Module ID
      if (incoming_buffer[INCOMING_SIZE - 1] == INCOMING_END_BYTE && incoming_buffer[1] == MODULE_ID) {

        OutgoingMessage message;

        message.start_val = OUTGOING_START_BYTE;
        message.module_id = MODULE_ID;
        message.command_id = incoming_buffer[2];
        message.data_value = 255;
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
