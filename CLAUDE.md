# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A 45-module (3 rows x 15 columns) split-flap display. Each module has an ATtiny1616 driving a 28BYJ-48 stepper motor with a hall-effect sensor for homing. A Raspberry Pi acts as the controller, communicating over RS485 half-duplex serial at 9600 baud.

There are three firmware generations:
- `firmware/drive_firmware/` — binary packet protocol (struct-based, 9-byte outgoing / 10-byte incoming), addressed by (row, column). This is what the `software/control/` Python code targets.
- `firmware/splitflapfirmwarev6/` — text-based protocol (e.g. `m04-A\n`), addressed by a 2-digit module ID (0–44). This is what the `frontend/app.py` Flask app targets. Protocol documented in `firmware/splitflapfirmwarev6/RS485.MD`.
- `firmware/splitflapfirmwarev7/` — text-based protocol with variable-length IDs (1–3 digits) and new `+` command for index-based flap moves. Includes `splitflap_test.py` interactive test tool.

## Commands

### Software layer (FastAPI + binary protocol)
```bash
cd software
pip install -r requirements.txt
uvicorn app.main:app --reload          # runs FastAPI server
python -m pytest control/test/         # run all tests
python -m pytest control/test/test_messages.py  # single test file
```

Tests use `unittest`. Some tests in `test_bus_controller.py` require physical hardware connected (hardcoded port `/dev/ttyACM0`).

### Frontend (Flask web UI — standalone)
```bash
pip install flask pyserial requests pytz yfinance
python frontend/app.py                    # runs on 0.0.0.0:80
```
The frontend is a standalone Flask app (`frontend/app.py` + `frontend/templates/index.html`) that talks directly to hardware via the v6 text protocol. It does not use the `software/control/` Python package.

### Firmware v7 test tool
```bash
pip install pyserial
python firmware/splitflapfirmwarev7/splitflap_test.py --port /dev/ttyUSB0
```
Interactive menu-driven RS485 test tool for the v7 text protocol.

### Firmware barebones comms test
```bash
# Flash test_comms/test_comms.ino, then:
python firmware/drive_firmware/test_comms/test_comms.py /dev/ttyUSB0
```
Sends a single byte and categorizes the response to isolate physical layer issues. See `firmware/drive_firmware/TROUBLESHOOTING.md` for step-by-step debugging.

### Firmware
Arduino IDE or `arduino-cli`. Upload `firmware/flash_eeprom/flash_eeprom.ino` first to set a module's row/column and initialize EEPROM positions, then upload the target firmware. Programming is done via UPDI using a modified USB-TTL board connected to the J1 header.

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

### software/ — FastAPI app + Python control layer (binary packet protocol)

The `software/` directory is a FastAPI application that wraps the binary protocol control layer:

```
software/
├── app/
│   ├── main.py          — FastAPI app, mounts routers and static files
│   ├── context.py       — lifespan handler: creates DisplayController, discovers modules on startup
│   ├── api/             — REST API routers (display, module, base) with Pydantic models
│   └── frontend/        — static frontend served by FastAPI
├── control/             — Python control layer (binary packet protocol)
│   ├── source/
│   │   ├── bus_controller.py      — concrete RS485 bus processor, owns ModuleControllers
│   │   ├── display_controller.py  — wraps BusController(s), auto-discovers modules
│   │   ├── serial_processor.py    — threaded queue worker, abstract base
│   │   ├── module_controller.py   — generates OutgoingMessage packets, tracks state
│   │   ├── dataclasses_.py        — OutgoingMessage/IncomingMessage structs
│   │   └── flaps.py               — Flap IntEnum (character set)
│   └── test/                      — unittest tests + mock firmware
├── requirements.txt
└── utils.py             — logging setup, timestamp helpers
```

Key data flow: `ModuleController._send_packet()` builds an `OutgoingMessage` → puts `(Future, message)` on the bus `Queue` → `SerialProcessor.worker()` encodes with a sequence ID → serial TX → serial RX → `BusController._handle_response()` decodes the `IncomingMessage` → `future.set_result(response)`.

### Control layer concurrency model

This is the heart of `control/` and spans `serial_processor.py`, `bus_controller.py`, and `module_controller.py`:

- **One worker thread per bus.** `BusController` (a `SerialProcessor`) starts a single daemon thread (`worker()`) that drains a `Queue`. The bus is half-duplex, so only **one command is in flight at a time** — the worker sends, blocks on the response, resolves the `Future`, then takes the next item. There is no pipelining.
- **Synchronous API over async transport.** Every `ModuleController` method (`home()`, `move_to_position()`, etc.) is blocking: it enqueues `(Future, message)` and calls `future.result()`, so callers experience a normal synchronous call while the actual serial I/O happens on the worker thread.
- **Sequence IDs** are assigned by the worker (not the message), increment per command, and **wrap at 255**. `_handle_response()` warns if the response's `sequence_id` doesn't match the outgoing one.
- **Latency** (send/receive/total ms) is measured by the worker and attached to each `IncomingMessage`.
- **`status` field drives errors.** A response with `status=False` carries a `ModuleErrorCodes` value in `data_value`; `ModuleController._handle_bad_status()` raises `FirmwareException`.
- **`DisplayController`** is a thin façade over one or more `BusController`s, flattening their `modules` dicts into a single `(row, col) → ModuleController` map and fanning batch operations (`move_to_flaps`, `move_all_to_position`) out to each module sequentially.

### Packet format (binary protocol)

Defined in `software/control/source/dataclasses_.py`. All packets use `struct.pack("<BBBBBHBB")` / `"<BBBBBH?BB"`:
- **OutgoingMessage** (controller→module): start=0x02, row, col, seq_id, cmd, data(2B), checksum, end=0x03 (9 bytes)
- **IncomingMessage** (module→controller): start=0x04, row, col, seq_id, cmd, data(2B), status, checksum, end=0x05 (10 bytes)
- Checksum: XOR of row, col, cmd, seq_id, data_low, data_high (and status for incoming)

### Module addressing

- Binary protocol: (row, column), each 0–255. EEPROM bytes 0–1 store row/column. **Row 0 or column 0 is reserved for broadcast** — modules act on a `(0,0)` message but do not reply (so the bus isn't flooded). `BusController.broadcast()` sends to `(0,0)`; the firmware's `isBroadcast()` matches `row==0 && column==0`.
- `BusController.discover(row_range, column_range)` PINGs every `(row, col)` in the **half-open ranges** `range(min, max)` (upper bound exclusive — e.g. `ROWS=[1,3]` probes rows 1–2), skipping any with row 0 or col 0, and registers a `ModuleController` for each that replies before a short timeout (default 0.05s).
- Text protocol (v6): flat module ID 0–44 (2-digit, zero-padded), stored in EEPROM byte 5.
- Text protocol (v7): variable-length module ID (1–3 digits), stored in EEPROM byte 5. Broadcast with `*` or `**`.

### EEPROM layout (drive_firmware)

Bytes 0–1: row, column. Bytes 2–129: 64 positions × 2 bytes each (step values for each flap position).

### EEPROM layout (v6/v7 firmware)

Byte 0: init flag (0x5D). Bytes 1–2: home offset. Bytes 3–4: total steps/rev. Byte 5: module ID. Byte 6: auto-home flag. Bytes 7–8: saved step position. Byte 9: saved flap index. Bytes 12–139: 64-entry position map (2 bytes each, 0xFFFF = uncalibrated).

### Motor constants

- 28BYJ-48: 4096 half-steps per revolution, 64 flap positions per drum, ~64 steps per flap.
- Hall sensor homing: motor steps until hall pin activates, then resets step counter to 0.

### frontend/app.py

Monolithic Flask app. Runs a background `playlist_loop` thread that cycles through display pages. Supports data apps (weather, stocks, sports, crypto, ISS, YouTube, transit), color animations, and a demo mode. Settings persisted to `/home/gordo/splitflap/settings.json`. The 45 modules are addressed by flat ID (0–44) mapped as `row * 15 + col`.

### Flap character set

Defined in `software/control/source/flaps.py` as a `Flap` IntEnum (56 values: blank, A–Z, symbols, colors). The v6/v7 firmware uses the string `" ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$&()-+=;q:%'.,/?*roygbpw"` (64 chars).

## Current state & known rough edges

The control library works against hardware, but the FastAPI wrapper around it is mid-refactor. Verify these before relying on them:

- **The FastAPI app does not start a display.** `app/context.py`'s `lifespan` has the `DisplayController`/`BusController`/`discover` setup commented out, so `app.state.display` is never created. Every `/api/v1` module/display endpoint (which depends on `get_display`) will fail, and teardown calls `app.state.display.close()` which will `AttributeError`. Uncomment and wire up `lifespan` to actually run the REST API.
- **Hardware-coupled defaults.** Port `/dev/ttyACM0` and the `ROWS=[1,3]/COLUMNS=[1,3]` discovery window are hardcoded in `context.py`; `drive_firmware.ino`'s `setup()` also hardcodes `MODULE_ROW=1, MODULE_COLUMN=1` and rewrites EEPROM on every boot rather than reading the flashed values via `getModuleRow()/getModuleColumn()`.
- **Known bugs in the control layer** (small, isolated — fix in place when touched): `DisplayController.home_all()` passes an undefined `position` to `module.home()`; `ModuleController._send_packet()` does `raise e` with `e` undefined on the exception path; `BusController._handle_response()` calls `self.error_queue(outgoing)` instead of `.put()` on a sequence-ID mismatch; `ModuleController.positions_known()` returns inverted logic; `control/test/mock_components/mock_module_firmware.py` references undefined `EXAMPLE_MESSAGE`/`message`.

### RS485 read/timeout behavior (control layer)

Notes from debugging `discover()` dropping modules that responded slightly late (logged in `software/discover_logs.txt`):

- **FIXED — discover producer/consumer race.** `discover()` used `future.result(self.timeout)`, a *producer-side* clock racing the worker's serial-read timeout. When a real module replied just after the producer gave up, the worker's later `set_result` landed on an abandoned future and the module was silently dropped. Fix: `discover()` now blocks on `future.result()` (no timeout), so it always waits for the worker's actual verdict — the single source of timeout truth — exactly like the normal `ModuleController._send_packet()` path. Do not reintroduce a producer-side timeout here.
- **FIXED — double timeout.** `_read_serial_response()` had a redundant poll loop that waited `self.timeout` *before* calling `read_packet()` (which waits another `self.timeout`), making every no-response read cost ~2× the configured timeout and causing the worker to lag the producer. The pre-poll was removed; `read_packet()` is now the single wait.
- **DEFERRED — `read_packet()` framing is fragile.** It gates on `in_waiting >= size` before reading, so it only starts parsing once a *full* packet is buffered. This works today only because the DTECH dongle echoes the 9-byte TX, padding the buffer right to the boundary when the real `0x04` start byte arrives. A byte-short or garbled reply will time out instead of being read. Robust fix (not yet applied): sync to the start byte gated on `in_waiting > 0`, then `connection.read(size - 1)` and validate length — **but** if switching to `connection.read(n)`, also make the `timeout` property setter (`serial_processor.py`) propagate to `self.connection.timeout`, which it currently does not (so a dynamically lowered `self.timeout` in `discover()` won't reach the serial port).
- **DEFERRED — worker counters only advance on success.** In `SerialProcessor.worker()`, `sequence_id += 1` and `queue.task_done()` run only in the success branch, not on the exception path. Latent risk of a late response being matched to the wrong command (PING responses skip the location sanity check in `_handle_response`). Fix: move both into a `finally`.
