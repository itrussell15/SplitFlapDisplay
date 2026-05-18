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
Arduino IDE. Upload `firmware/flash_eeprom/flash_eeprom.ino` first to set a module's row/column and initialize EEPROM positions, then upload `firmware/drive_firmware/drive_firmware.ino` (or `splitflapfirmwarev6/` for the text protocol).

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
