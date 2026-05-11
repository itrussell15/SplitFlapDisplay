int INCOMING_SIZE = 7;
byte INCOMING_START_BYTE = 2;
byte INCOMING_END_BYTE = 3;

// Changed to 8 to match your data, or remove the 8th value
int OUTGOING_SIZE = 8; 
byte OUTGOING_START_BYTE = 4;
byte OUTGOING_END_BYTE = 5;

byte MODULE_ID = 1;

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
        // Send the whole response at once
        outgoing_buffer[2] = incoming_buffer[2];
        int response = handle_incoming_command(incoming_buffer[2], incoming_buffer[3]);
        if (response < 0)
        {
          // Set status to false
          outgoing_buffer[3] = 0;
          outgoing_buffer[4] = false;
          
        }
        Serial.write(outgoing_buffer, OUTGOING_SIZE);
        
        // Blink LED to confirm successful TX
        digitalWrite(LED_BUILTIN, LOW);
        delay(50);
        digitalWrite(LED_BUILTIN, HIGH);
      }
    } else {
      Serial.read(); // Discard trash
    }
  }
}

int handle_incoming_command(int command_value, int data_value)
{
  int output_value = 1;
  if (command_value > 2)
  {
    output_value = -1;
  }
  return output_value;
}
