
void setup() {
  Serial.begin(9600);
  while (!Serial) { ; } // Wait for port to connect
//  Serial.println("Waiting for input... (1 second window starts on first byte)");
}

void loop() {
  // Wait until the first byte of data arrives
  if (Serial.available() > 0) {
    String buffer = "";
    unsigned long startTime = millis();

    // Keep reading for exactly 1000 milliseconds (1 second)
    while (millis() - startTime < 100) {
      if (Serial.available() > 0) {
        char c = Serial.read();
        buffer += c; // Append the character to our string
      }
    }

    // After 1 second, return the collected data
    if (buffer.length() > 0) {
//      Serial.print("Returned: ");
      Serial.println(buffer);
    }
  }
}
