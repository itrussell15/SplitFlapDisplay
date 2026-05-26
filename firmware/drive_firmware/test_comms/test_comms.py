"""
Barebones RS485 communication test.

Sends a single byte (0x01) and analyzes what comes back.
Flash test_comms.ino to the module first.

The module should respond with 0xAA 0xBB 0xCC regardless of what byte is sent.
The status LED (D1) on the module will blink on each received byte.

Dongle wiring (DTECH USB-RS485, half-duplex):
    T/R+  -> Board A pad
    T/R-  -> Board B pad
    GND   -> J1 pin 2 (UPDI header, middle pin)
    RXD+  -> (leave unconnected)
    RXD-  -> (leave unconnected)

Usage:
    python test_comms.py /dev/ttyUSB0
"""

import serial
import sys
import time

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
BAUD = 9600
SEND_BYTE = b"\x01"
EXPECTED_RESPONSE = bytes([0xAA, 0xBB, 0xCC])


def run_test():
    ser = serial.Serial(PORT, BAUD, timeout=1)
    ser.reset_input_buffer()
    time.sleep(0.1)

    print(f"Port: {PORT} @ {BAUD} baud")
    print(f"Sending: 0x{SEND_BYTE.hex()}")
    ser.write(SEND_BYTE)

    time.sleep(0.5)
    raw = ser.read(ser.in_waiting or 10)
    ser.close()

    print(f"Received ({len(raw)} bytes): {raw.hex(' ') if raw else '(nothing)'}\n")

    if len(raw) == 0:
        print("RESULT: No data received.")
        print("  - Is the module powered (12V)?")
        print("  - Is the correct serial port selected?")
        print("  - Check dongle wiring: T/R+ -> A, T/R- -> B, GND -> J1 pin 2")
        return

    has_echo = raw[:1] == SEND_BYTE
    has_response = EXPECTED_RESPONSE in raw

    if has_echo and has_response:
        print("RESULT: Echo + module response.")
        print("  - Dongle echoes its own TX on T/R lines (expected).")
        print("  - Module is responding correctly.")
        print(f"  - Echo:     0x{raw[:1].hex()}")
        print(f"  - Response: 0x{raw[1:].hex(' ')}")
        print("\n  Next: flash drive_firmware.ino and run the full protocol test.")

    elif has_response and not has_echo:
        print("RESULT: Module response only, no echo.")
        print("  - Clean communication, everything works.")
        print("\n  Next: flash drive_firmware.ino and run the full protocol test.")

    elif has_echo and not has_response:
        print("RESULT: Echo only, no module response.")
        print("  - The dongle is echoing its own transmission.")
        print("  - The module is NOT responding.")
        print("  Diagnose with the LED:")
        print("    - LED (D1) blinked? -> Module received data but transmit path is broken.")
        print("      Check: PA5 -> U3 pin 4, DE pin (PA6) toggling, A/B wiring back to dongle.")
        print("    - LED did NOT blink? -> Module is not receiving.")
        print("      Check: A/B polarity (T/R+ -> A, T/R- -> B), GND connected,")
        print("             module powered, 3.3V present on U3 pin 8.")

    else:
        print("RESULT: Unexpected data.")
        print("  - Neither a clean echo nor the expected 0xAA 0xBB 0xCC response.")
        print(f"  - Raw bytes: {raw.hex(' ')}")
        print("  - Possible noise, baud rate mismatch, or A/B polarity swap.")


if __name__ == "__main__":
    run_test()
