#include <SoftwareSerial.h>

const int RS485_RX = 3;
const int RS485_TX = 1;
const int RS485_DE = 2;

SoftwareSerial rs485(RS485_RX, RS485_TX);

const int STATUS_LED_PIN = PIN_PA3;
const byte RESPONSE[] = {0xAA, 0xBB, 0xCC};

void setup() {
  rs485.begin(9600);
  pinMode(RS485_DE, OUTPUT);
  digitalWrite(RS485_DE, LOW);
  pinMode(STATUS_LED_PIN, OUTPUT);
}

void loop() {
  if (rs485.available()) {
    byte received = rs485.read();

    // Drain any remaining bytes
    while (rs485.available()) {
      rs485.read();
    }

    // Blink LED to confirm we received something
    digitalWrite(STATUS_LED_PIN, HIGH);

    delay(50);
    digitalWrite(RS485_DE, HIGH);
    delay(10);

    for (int i = 0; i < sizeof(RESPONSE); i++) {
      rs485.write(RESPONSE[i]);
    }

    delay(100);
    digitalWrite(RS485_DE, LOW);

    digitalWrite(STATUS_LED_PIN, LOW);
  }
}
