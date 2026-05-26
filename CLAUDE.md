# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A 45-module (3 rows x 15 columns) split-flap display. Each module has an Arduino driving a 28BYJ-48 stepper motor with a hall-effect sensor for homing. A Raspberry Pi acts as the controller, communicating over RS485 half-duplex serial at 9600 baud.

There are two firmware generations in use:
- `firmware/drive_firmware/` — binary packet protocol (struct-based, 9-byte outgoing / 10-byte incoming), addressed by (row, column). This is what the `control/` Python code targets.
- `firmware/splitflapfirmwarev6/` — text-based protocol (e.g. `m04-A\n`), addressed by a flat module ID (0–44). This is what the `frontend/app.py` Flask app targets.

## Commands

### Python control layer
```bash
pip install -r control/requirements.txt   # just pyserial
python -m pytest control/test/            # run all tests
python -m pytest control/test/test_messages.py  # single test file
```

Tests use `unittest`. Some tests in `test_bus_controller.py` require physical hardware connected (hardcoded port `/dev/cu.usbmodem1101`).

### Frontend (Flask web UI)
```bash
pip install flask pyserial requests pytz yfinance
python frontend/app.py                    # runs on 0.0.0.0:80
```
The frontend is a standalone Flask app (`frontend/app.py` + `frontend/templates/index.html`) that talks directly to hardware via the v6 text protocol. It does not use the `control/` Python package.

### Firmware
Arduino IDE. Upload `firmware/flash_eeprom/flash_eeprom.ino` first to set a module's row/column and initialize EEPROM positions, then upload `firmware/drive_firmware/drive_firmware.ino` (or `splitflapfirmwarev6/` for the text protocol). Programming is done via UPDI using a modified USB-TTL board connected to the J1 header.

## PCB and Pin Mapping

KiCad schematics and PCB files are in `PCBs/driver-v3/` (latest) and `PCBs/driver-v2/`.

### Pin mapping (non-standard)

The firmware uses a **non-standard Arduino pin numbering** that counts clockwise around the QFN-20 package starting from PA4. This is NOT the megaTinyCore default (PA0=0, PA1=1, ...). Key mappings:

| Arduino Pin | ATtiny Port | Package Pin | Function |
|-------------|-------------|-------------|----------|
| 1 | PA5 | 6 | RS485 TX (SoftwareSerial) |
| 2 | PA6 | 7 | RS485 DE/RE |
| 3 | PA7 | 8 | RS485 RX (SoftwareSerial) |
| 4 | PB5 | 9 | Hall sensor |
| 6 | PB3 | 11 | Stepper IN4 |
| 7 | PB2 | 12 | Stepper IN3 |
| 8 | PB1 | 13 | Stepper IN2 |
| 9 | PB0 | 14 | Stepper IN1 |
| PIN_PA3 | PA3 | 2 | Status LED (D1) |

### RS485 wiring (verified from KiCad)

- SN65HVD72DR (U3): R→PA7, D→PA5, RE+DE tied together→PA6. Runs on 3.3V from U5 regulator.
- Both firmwares must use `SoftwareSerial` on pins 3 (RX) and 1 (TX). Hardware `Serial.begin()` puts RX on PA2 which conflicts with the DE pin — the module cannot receive.
- RS485 responses require timing delays before/after toggling DE: 50ms before DE HIGH, 10ms after DE HIGH, 100ms after transmit before DE LOW.
- The USB-RS485 dongle (DTECH) echoes all transmitted bytes on the T/R lines. Software must discard echo bytes.

### UPDI programming header (J1)

Pin 1: +3V3, Pin 2: GND, Pin 3: UPDI. If a USB-TTL programmer is soldered to J1, it back-powers through pin 1 when the module has 12V, dragging down the 3.3V rail. Always disconnect the programmer before testing RS485, or cut the J1 pin 1 trace.

### LED usage

The status LED (D1) is on PA3 via R2 (60Ω). Use `PIN_PA3` in code — do NOT use `LED_BUILTIN` (defaults to PA7, which is the RS485 RX pin).

### Dongle wiring (DTECH USB-RS485)

5 screw terminals: T/R+, T/R-, RXD+, RXD-, GND. For half-duplex: T/R+ → board A pad, T/R- → board B pad, GND → J1 pin 2. Leave RXD+/RXD- unconnected.

## Architecture

### control/ — Python control layer (binary packet protocol)

```
SerialControl          — low-level serial read/write/read_packet
    └─ SerialProcessor — threaded queue worker, encodes+sends messages, reads+dispatches responses (abstract)
        └─ BusController — concrete processor for one RS485 bus; owns a dict of ModuleControllers keyed by (row, col)
            └─ DisplayController — (WIP) wraps BusController, auto-discovers modules on init

ModuleController — generates OutgoingMessage packets and pushes them onto BusController's queue; tracks module state
```

Key data flow: `ModuleController._create_packet()` → `Queue` → `SerialProcessor.worker()` encodes with sequence ID → serial TX → serial RX → `BusController._handle_response()` decodes `IncomingMessage` → dispatches by command type.

### Packet format (binary protocol)

Defined in `control/source/dataclasses_.py`. All packets use `struct.pack("<BBBBBHBB")` / `"<BBBBBH?BB"`:
- **OutgoingMessage** (controller→module): start=0x02, row, col, seq_id, cmd, data(2B), checksum, end=0x03 (9 bytes)
- **IncomingMessage** (module→controller): start=0x04, row, col, seq_id, cmd, data(2B), status, checksum, end=0x05 (10 bytes)
- Checksum: XOR of row, col, cmd, seq_id, data_low, data_high (and status for incoming)

### Module addressing

- Binary protocol: (row, column), each 0–255. EEPROM bytes 0–1 store row/column.
- Text protocol (v6): flat module ID 0–44, stored in EEPROM byte 5.

### EEPROM layout (drive_firmware)

Bytes 0–1: row, column. Bytes 2–129: 64 positions × 2 bytes each (step values for each flap position).

### Motor constants

- 28BYJ-48: 4096 half-steps per revolution, 64 flap positions per drum, ~64 steps per flap.
- Hall sensor homing: motor steps until hall pin activates, then resets step counter to 0.

### frontend/app.py

Monolithic Flask app. Runs a background `playlist_loop` thread that cycles through display pages. Supports data apps (weather, stocks, sports, crypto, ISS, YouTube, transit), color animations, and a demo mode. Settings persisted to `/home/gordo/splitflap/settings.json`. The 45 modules are addressed by flat ID (0–44) mapped as `row * 15 + col`.

### Flap character set

Defined in `control/source/flaps.py` as a `Flap` IntEnum (56 values: blank, A–Z, symbols, colors). The v6 firmware uses the string `" ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$&()-+=;q:%'.,/?*roygbpw"` (64 chars).
