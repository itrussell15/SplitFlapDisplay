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

Hardware diagnostics / calibration (run from `software/control/`, binary protocol):
```bash
python diagnose_comms.py --port /dev/ttyUSB1 -n 100 [--interleave] [--settle 0.02]  # RS485 reliability harness
python eeprom_roundtrip.py --port /dev/ttyUSB1 --row 1 --col 1 --index 5            # EEPROM save/retrieve + persistence
python test/calibration.py   # interactive flap calibration (homes first, jog + SET_POSITION per flap)
```

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
Arduino IDE or `arduino-cli`. Programming is done via UPDI using a modified USB-TTL board connected to the J1 header. Per module: edit `MODULE_ROW`/`MODULE_COLUMN` in `firmware/flash_eeprom/flash_eeprom.ino`, upload it first (sets row/column + seeds EEPROM positions), then upload `drive_firmware`. **Set "Save EEPROM: EEPROM retained" (Burn Bootloader once to write the EESAVE fuse) before the `drive_firmware` upload**, or the chip-erase wipes the address `flash_eeprom` wrote and the module comes up at `(255,255)` and won't respond. See Known rough edges → Flashing workflow.

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
- **The USB-RS485 dongle does NOT echo transmitted bytes** (verified 2026-06-09 via `software/control/diagnose_comms.py`: every captured `RX` is the bare 10-byte module reply starting `0x04`, with no `0x02…` TX echo prefix). An earlier note here claimed the DTECH dongle echoes all TX bytes — that is false for the current hardware, and `read_packet()`'s framing was mistakenly built around that assumption (see Known rough edges). Do not write code that depends on an echo.
- **The link is electrically healthy.** `diagnose_comms.py` shows ~99–100% clean replies (no corruption, no clipping, no checksum errors) even at a 20ms cadence. Replies that come back are always byte-perfect, so the intermittent-comms problems were NOT signal integrity / termination / biasing.

- **ROOT CAUSE of the intermittent dropped commands (FIXED 2026-06-09): the frame start byte `0x02` collides with module addresses, and the firmware mis-framed on it.** `OutgoingMessage.start_value` is `0x02`, and module **column 2 is the byte `0x02`**. On the shared half-duplex bus every module hears every other module's *replies*, and module 2's reply carries `0x02` in its column field. The old `drive_firmware` parser gated on `available() >= INCOMING_SIZE`, trusted any `0x02` as a frame start, and read a full 9-byte frame — so a stray `0x02` inside another module's reply swallowed the **real start byte of the very next command**, silently dropping it. Symptom: whichever module is addressed immediately after module 2 transmits fails ~100% of the time; isolated/single-module traffic looks fine, which is why it presented as "intermittent."
  - Confirmed empirically with `diagnose_comms.py --interleave`: addressing `1,1 1,2 1,4` round-robin → (1,4) failed 100% (it follows (1,2)). Reordering to `1,1 1,4 1,2` moved the 100% failure to (1,1). Removing (1,2) from the set made the rest ~100% reliable.
  - **Fix:** `drive_firmware.ino` now parses incrementally via `serviceIncomingSerial()` / `processIncomingFrame()` — sync on the start byte gated on `available() > 0`, accumulate a candidate frame, validate the **end byte** (and checksum), and on a false start discard only **one** byte and re-scan, so a `0x02` embedded in other traffic can't eat a real command. Do NOT revert to the `available() >= size` + read-9-on-any-`0x02` approach.

- **Residual ~1–2% "first ping after idle" miss.** After the framing fix, the only remaining drops are the very first transaction to a module after the bus has been idle (a cold-start/turnaround effect, not corruption). Mitigated on the controller side by bounded retry — `SerialProcessor.worker()` re-sends the same command (same sequence_id, with `reset_input_buffer()` first) up to `self.max_retries` times. If you want to chase the last fraction of a percent in hardware, add RS485 fail-safe biasing (~560Ω A→+3V3, ~560Ω B→GND once on the bus) and 120Ω termination at both physical ends.

- **`software/control/diagnose_comms.py`** is the echo-agnostic raw-capture reliability harness used to find all of the above: it pings any set of addresses N times, dumps the full raw RX buffer, classifies each result (OK / NO_REPLY / CLIPPED_HEAD / SHORT / BAD_CHECKSUM / BAD_END / GARBAGE), and prints a per-attempt timeline. Use `--interleave` to reproduce multi-module bus contention and `--settle` to vary cadence.

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

Byte 0: row. Byte 1: column. Bytes 2–3: unused gap. Bytes 4–131: 64 positions × 2 bytes each (absolute step value for each flap, little-endian `uint16_t`, `0xFFFF` = uncalibrated on a blank chip). The position offset is `(index + 2) * 2` — `flash_eeprom.ino` and `drive_firmware.ino` (`saveStepperPosition`/`getStepperPosition`) **must use the identical `index += 2` offset** or seeded positions read back shifted by one index (this was a real bug: `flash_eeprom` used `index += 1`, fixed 2026-06-15).

### EEPROM layout (v6/v7 firmware)

Byte 0: init flag (0x5D). Bytes 1–2: home offset. Bytes 3–4: total steps/rev. Byte 5: module ID. Byte 6: auto-home flag. Bytes 7–8: saved step position. Byte 9: saved flap index. Bytes 12–139: 64-entry position map (2 bytes each, 0xFFFF = uncalibrated).

### Motor constants

- 28BYJ-48: **4096 half-steps = one full revolution** (verified on hardware 2026-06-15 — one rotation shows all 64 characters), 64 flap positions per drum, ~64 steps per flap.
- **`Stepper.cpp` `RESOLUTION` must be 4096.** It was wrongly set to `12288` (4096×3), which made the step counter span ~3 physical revolutions: every physical flap mapped to 3 different counter values (ambiguous) and moves could spin extra rotations. Fixed to 4096.
- Hall sensor homing: motor steps until hall pin activates, then resets step counter to 0.
- **Positions are absolute step counts, only meaningful relative to a homed (hall) zero.** `drive_firmware` does NOT persist `currentStep`, so it **auto-homes on boot** (`motor.home()` in `setup()`) to re-anchor step 0. Without homing, a stored position lands on a different physical flap after any reset (this was the "calibrated spot moved" bug). Calibration must therefore home first (`calibration.py` does), and `CMD_MOVE_TO_POSITION` guards against uncalibrated `0xFFFF` (→ `-1` as a 16-bit int) via `isValidStep` so the motor can't chase an unreachable target forever.

### Motor holding / release (calibration repeatability)

- All firmware generations **de-energize the coils at rest** (`drive_firmware` `motor.release()`, v6/v7 `releaseMotor()`). The original design relies on the magnetic detent to hold position — fine for *displaying* characters, but it costs repeatability: because moves are half-stepped, the rest position is often between full-step detents, so releasing snaps the rotor ±1 half-step. Many small moves (incremental calibration) accumulate this; one large move doesn't — which is why calibrating spot-by-spot landed differently than a single long move.
- `drive_firmware` now (2026-06-15) holds briefly before releasing: `motorStepTiming()` steps while moving (`STEP_INTERVAL_MICROS`, `micros()` base), and when at target `motorHoldTiming()` keeps the coils energized for `RELEASE_INTERVAL_MICROS` (500 ms) then releases — long enough to settle, short enough to keep aggregate heat/current low across 45 modules. **Both step and hold timers must share the same `micros()` time base** (a `millis()`/`micros()` mix is a silent bug: it makes stepping ~1/s and releases immediately).
- `CMD_TOGGLE_CALIBRATION_MODE` (command 20): in calibration mode the module **never releases** (holds indefinitely so you judge/teach against the energized position) and uses a slower step rate (~3000 µs vs 1000 µs) for accuracy. `STEP_INTERVAL_MICROS` is therefore mutable at runtime — it must NOT be declared `const`.
- 28BYJ-48 tolerates continuous energization (warm, safe per-motor); the reason to release promptly is **aggregate** power/heat at 45 modules, not single-motor safety.

### frontend/app.py

Monolithic Flask app. Runs a background `playlist_loop` thread that cycles through display pages. Supports data apps (weather, stocks, sports, crypto, ISS, YouTube, transit), color animations, and a demo mode. Settings persisted to `/home/gordo/splitflap/settings.json`. The 45 modules are addressed by flat ID (0–44) mapped as `row * 15 + col`.

### Flap character set

Defined in `software/control/source/flaps.py` as a `Flap` IntEnum (56 values: blank, A–Z, symbols, colors). The v6/v7 firmware uses the string `" ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$&()-+=;q:%'.,/?*roygbpw"` (64 chars).

## Current state & known rough edges

The control library works against hardware, but the FastAPI wrapper around it is mid-refactor. Verify these before relying on them:

- **The FastAPI app does not start a display.** `app/context.py`'s `lifespan` has the `DisplayController`/`BusController`/`discover` setup commented out, so `app.state.display` is never created. Every `/api/v1` module/display endpoint (which depends on `get_display`) will fail, and teardown calls `app.state.display.close()` which will `AttributeError`. Uncomment and wire up `lifespan` to actually run the REST API.
- **Hardware-coupled defaults.** Port `/dev/ttyACM0` and the `ROWS=[1,3]/COLUMNS=[1,3]` discovery window are hardcoded in `context.py`. (`drive_firmware.ino`'s `setup()` now correctly reads its address from EEPROM via `getModuleRow()/getModuleColumn()` and no longer overwrites it — fixed 2026-06-15.)

- **Flashing workflow — EEPROM must survive the `drive_firmware` upload.** Because `drive_firmware` now *depends* on the address `flash_eeprom.ino` wrote (it self-assigns nothing), two things must hold: (1) **set distinct `MODULE_ROW`/`MODULE_COLUMN` per unit in `flash_eeprom.ino`** before flashing each module (its defaults are `1,3` — flashing several unmodified makes them all `(1,3)`); and (2) **enable EEPROM retention** so the UPDI chip-erase during the `drive_firmware` upload doesn't wipe what `flash_eeprom` wrote. In the Arduino IDE that's Tools → "Save EEPROM" → "EEPROM retained", then Burn Bootloader (writes the EESAVE fuse), *then* flash `flash_eeprom`, *then* `drive_firmware`. Symptom of a wiped EEPROM: `getModuleRow/Column` read `0xFF` so the module believes it's at `(255,255)` and ignores all commands — looks like a dead/uncommunicative module. Confirm with `bus.discover([255,256],[255,256])`.
- **Known bugs in the control layer** (small, isolated — fix in place when touched): `DisplayController.home_all()` passes an undefined `position` to `module.home()`; `ModuleController._send_packet()` does `raise e` with `e` undefined on the exception path; `BusController._handle_response()` calls `self.error_queue(outgoing)` instead of `.put()` on a sequence-ID mismatch; `ModuleController.positions_known()` returns inverted logic; `control/test/mock_components/mock_module_firmware.py` references undefined `EXAMPLE_MESSAGE`/`message`.

### RS485 read/timeout behavior (control layer)

Notes from debugging `discover()` dropping modules that responded slightly late (logged in `software/discover_logs.txt`):

- **FIXED — discover producer/consumer race.** `discover()` used `future.result(self.timeout)`, a *producer-side* clock racing the worker's serial-read timeout. When a real module replied just after the producer gave up, the worker's later `set_result` landed on an abandoned future and the module was silently dropped. Fix: `discover()` now blocks on `future.result()` (no timeout), so it always waits for the worker's actual verdict — the single source of timeout truth — exactly like the normal `ModuleController._send_packet()` path. Do not reintroduce a producer-side timeout here.
- **FIXED — double timeout.** `_read_serial_response()` had a redundant poll loop that waited `self.timeout` *before* calling `read_packet()` (which waits another `self.timeout`), making every no-response read cost ~2× the configured timeout and causing the worker to lag the producer. The pre-poll was removed; `read_packet()` is now the single wait.
- **DEFERRED — `read_packet()` framing is fragile and rests on a false premise.** It gates on `in_waiting >= size` before reading, so it only starts parsing once a *full* packet is buffered. The original rationale was that the dongle echoes the 9-byte TX, padding the buffer to the boundary — **but the dongle does not echo** (see RS485 wiring), so that rationale is invalid. In practice the bare 10-byte reply does reach `in_waiting >= size` on its own, so the happy path works, but a byte-short or garbled reply will time out instead of being read, and the byte-at-a-time scan discards partial frames so they're never surfaced. Robust fix (not yet applied): sync to the `0x04` start byte gated on `in_waiting > 0`, then `connection.read(size - 1)` and validate length + end byte — **but** if switching to `connection.read(n)`, also make the `timeout` property setter (`serial_processor.py`) propagate to `self.connection.timeout`, which it currently does not (so a dynamically lowered `self.timeout` in `discover()` won't reach the serial port). NOTE: `serial_processor.py`'s `worker()` already calls `reset_input_buffer()` before each send and applies a `command_interval` guard delay; `software/control/diagnose_comms.py` is an echo-agnostic raw-capture reliability harness used to characterise the link.
- **FIXED — worker counters only advance on success.** `sequence_id` and `queue.task_done()` now run in a `finally` in `SerialProcessor.worker()`, once per command regardless of outcome, so a timed-out command no longer desyncs the sequence numbering of the commands after it.
- **ADDED — bounded retry + input flush + turnaround guard in the worker.** `worker()` delegates each command to `_process_command()`, which: (1) calls `reset_input_buffer()` before every attempt so stale/late bytes can't misalign the read; (2) re-sends the **same** command with the **same** `sequence_id` up to `self.max_retries` times (default 2) on timeout/malformed reply, catching transient single misses like the cold-start drop; and (3) sleeps `self.command_interval` (default 20ms) after each attempt so the half-duplex module finishes its DE turnaround before the next TX. Retrying is safe because all current module commands are idempotent (absolute moves, gets, ping, home). Tunable via `bus.max_retries` / `bus.command_interval`.
