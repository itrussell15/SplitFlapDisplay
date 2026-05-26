# RS485 Communication Troubleshooting

## Background

The drive_firmware had a bug where `Serial.begin()` (hardware USART0) placed RX on PA2 — the same pin used for RS485 DE direction control. This meant the module could never receive data. The fix switches to `SoftwareSerial` on pins 3 (RX) and 1 (TX), matching the PCB wiring and the working v6 firmware.

## PCB Wiring Reference (Verified from KiCad)

### RS485 Transceiver (U3 — SN65HVD72DR)

| U3 Pin | Function | Net | ATtiny1616 Port | Arduino Pin |
|--------|----------|-----|-----------------|-------------|
| 1 | R (Receiver Output) | `RXD` | PA7 | 3 |
| 2 | RE (Receiver Enable) | `DE/RE` | PA6 | 2 |
| 3 | DE (Driver Enable) | `DE/RE` | PA6 | 2 |
| 4 | D (Driver Input) | `TXD` | PA5 | 1 |
| 6 | A | `RS465_A` | → A pad on board | |
| 7 | B | `RS465_B` | → B pad on board | |

RE and DE are tied together on the PCB (`DE/RE` net) — correct half-duplex wiring controlled by a single GPIO.

### Status LED (D1)

ATtiny PA3 → R2 (60Ω current limiter) → D1 (LED) → GND

The LED is on `PIN_PA3`. Do NOT use `LED_BUILTIN` — megaTinyCore defaults that to PA7, which is the RS485 RXD pin on this board.

### Other Components

- **R1 (0Ω):** Bridges `+VBUS` to `+VBUSF` (power rail jumper). Not related to RS485.
- **R2 (60Ω):** LED current-limiting resistor. Not a bus termination resistor.

### UPDI Programming Header (J1)

| Pin | Net |
|-----|-----|
| 1 | +3V3 |
| 2 | GND |
| 3 | UPDI |

### UPDI Programmer and Back-Powering

**WARNING:** If a USB-TTL programmer is soldered to J1, it will back-power itself through J1 pin 1 (+3V3) whenever the module is powered from 12V — even if the USB cable is unplugged. You'll see the TTL board's LED light up. This causes two problems:

1. **Drains the 3.3V rail** — the SPX3819M5-L-3-3 (U5) is a small LDO only meant to power the ATtiny and the RS485 transceiver. An entire USB-TTL board drawing additional current can pull the 3.3V rail low enough that U3 can't drive the RS485 bus reliably.
2. **TTL chip I/O pins become active** — the back-powered chip's TX pin (connected to UPDI/PA0) enters an indeterminate state, adding noise and unpredictable current draw.

**Never have both 12V power and the USB-TTL programmer connected at the same time** (unless you cut the J1 pin 1 trace — see below).

#### Recommended workflow (no board modification)

1. Unplug 12V power
2. Plug in USB-TTL → flash firmware via UPDI (programmer powers the ATtiny through J1 pin 1)
3. Unplug USB-TTL
4. Plug in 12V → test RS485

#### Optional board modification for faster iteration

Cut the J1 pin 1 trace (+3V3) and optionally add a jumper or switch. With this cut:

- The programmer gets power only from USB, the module gets power only from 12V → 3.3V regulator
- The only shared connections are GND (J1 pin 2) and UPDI signal (J1 pin 3)
- Both can be safely connected at the same time — no voltage contention, no back-powering
- UPDI programming still works because it only needs GND and the signal line; the target is powered by its own 12V supply

This lets you flash and test without swapping cables:
1. Keep 12V on
2. Plug USB into TTL board → flash
3. Unplug USB from TTL board → test RS485 immediately

## Dongle Wiring (DTECH USB-RS485)

The dongle has 5 screw terminals: `T/R+`, `T/R-`, `RXD+`, `RXD-`, `GND`.

For half-duplex, only use the `T/R` pair:

```
Dongle              Board
──────              ─────
T/R+  ────────────  A pad
T/R-  ────────────  B pad
GND   ────────────  J1 pin 2 (UPDI header, middle pin)
RXD+                (leave unconnected)
RXD-                (leave unconnected)
```

The `T/R` lines are a combined transmit/receive half-duplex pair. The dongle's receiver is always enabled on these lines, so **it will echo back everything it transmits**. This is expected — handle it in software by discarding the first N bytes (equal to what was sent) before reading the module's response.

---

## Step 1: Isolate the USB-RS485 Dongle

Before flashing any firmware, confirm whether the dongle echoes.

1. **Disconnect the module board** — remove the A/B wires from the dongle entirely.
2. Open a serial terminal (e.g. `screen`, PuTTY, Arduino Serial Monitor) at 9600 baud.
3. Send a few bytes.
4. **If you see them echoed back** — the dongle echoes its own transmissions. This is expected with the T/R lines. You'll need to strip echo bytes in your Python control layer.
5. **If you see nothing** — the dongle does not echo. Any echo you see later is coming from somewhere else.

## Step 2: Barebones Communication Test

Before testing the full binary protocol, use the stripped-down test in `test_comms/` to verify basic bidirectional RS485 communication. This eliminates protocol complexity (checksums, addressing, packet framing) and isolates the physical layer.

### What it does

- **`test_comms.ino`** — Minimal firmware. On receiving any byte, responds with a fixed 3-byte sequence: `0xAA 0xBB 0xCC`. Blinks the status LED (D1, on PA3) on every received byte.
- **`test_comms.py`** — Sends a single byte (`0x01`) and categorizes what comes back.

### Procedure

1. **Unplug 12V power.**
2. **Disconnect the RS485 dongle** from the board.
3. Plug in the USB-TTL programmer and flash `test_comms/test_comms.ino` via UPDI.
4. **Unplug the USB-TTL programmer.** If soldered to J1, desolder or disconnect it. The TTL board will back-power through J1 pin 1 and drag down the 3.3V rail (see "UPDI Programmer and Back-Powering" above).
5. Wire the dongle to the board:
   - `T/R+` → A pad
   - `T/R-` → B pad
   - `GND` → J1 pin 2 (UPDI header middle pin)
6. **Power the module (12V supply).**
7. Run the test:
   ```bash
   python test_comms/test_comms.py /dev/ttyUSB0
   ```

### Interpreting results

| Output | Meaning | Next step |
|---|---|---|
| `Echo + module response` (4 bytes: `01 aa bb cc`) | Working. Dongle echoes, module responds. | Dongle echo is expected with T/R lines. Move to Step 3. |
| `Module response only` (3 bytes: `aa bb cc`) | Working perfectly, no dongle echo. | Move to Step 3. |
| `Echo only` (1 byte: `01`) | Module is not responding. | Check LED on module (see below). If no blink: wiring/receive path issue (Step 4). If blink: transmit path issue (Step 4). |
| `No data received` (0 bytes) | No communication at all. | Check serial port, baud rate, 12V power, and A/B wiring. |

### What the LED tells you

The status LED (D1) blinks on every byte received by the module:

- **LED blinks when you send data** — the receive path works (dongle → A/B bus → U3 pin 1 R → ATtiny PA7). If no `0xAA 0xBB 0xCC` comes back, the **transmit path** is the problem: check ATtiny PA5 → U3 pin 4 D → A/B bus → dongle T/R lines, and verify DE (PA6) is toggling correctly.
- **LED never blinks** — the **receive path** is broken. Check: A/B wiring polarity (A-to-A, B-to-B), dongle GND connected to J1 pin 2, module is powered, U3 has 3.3V on pin 8.

## Step 3: Full Protocol Test

Once the barebones test passes, flash `drive_firmware.ino` and test the real binary protocol.

Send a CMD_PING (command 0) packet to the module's row/column. The 9-byte outgoing packet format is:

```
[0x02] [row] [col] [seq_id] [cmd] [data_low] [data_high] [checksum] [0x03]
```

For a ping to module (0, 0) with sequence ID 1:
```
0x02  0x00  0x00  0x01  0x00  0x00  0x00  0x01  0x03
```
Checksum = row ^ col ^ cmd ^ seq_id ^ data_low ^ data_high = 0x00 ^ 0x00 ^ 0x00 ^ 0x01 ^ 0x00 ^ 0x00 = 0x01

**Expected response** (10 bytes):
```
[0x04] [row] [col] [seq_id] [cmd] [data_low] [data_high] [status] [checksum] [0x05]
```

### Interpreting results

| What you see | Meaning | Next step |
|---|---|---|
| 9-byte echo + 10-byte response (19 bytes) | Working. Dongle echoes, module responds. | Handle echo in software (discard first 9 bytes). |
| 10-byte response only, starts with 0x04 | Working perfectly, no echo. | Done. |
| 9-byte echo only, no response | Module isn't responding. | Go to Step 4. |
| Nothing at all | No communication. | Check wiring, baud rate, correct serial port. |

## Step 4: Module Not Responding

If you see your sent bytes echoed but no module response:

### Check the module's row/column identity
The module reads its row and column from EEPROM bytes 0 and 1. If these don't match the row/col in your packet, the module silently ignores it. Flash `flash_eeprom.ino` first to set known values, then re-flash `drive_firmware.ino`.

### Check the LED for activity
The status LED (D1, on PA3) blinks when the firmware receives a byte that doesn't match the start byte (0x02). If the LED blinks when you send data, the module IS receiving but discarding bytes (possibly a framing issue). If the LED never blinks and no response comes, the module isn't receiving at all.

### Check A/B polarity
Make sure A connects to A (dongle T/R+ → board A pad) and B connects to B (dongle T/R- → board B pad). Swapped polarity inverts the signal and the transceiver won't decode it.

### Check GND connection
A shared ground reference between the dongle and the board is important for signal integrity. Connect the dongle's GND terminal to J1 pin 2 (UPDI header middle pin).

### Check for UPDI programmer back-powering
If a USB-TTL programmer is soldered to J1, check whether its LED is lit while the module is powered from 12V. If it is, the programmer is draining the 3.3V rail. Disconnect it before testing (see "UPDI Programmer and Back-Powering" above).

### Check power
Verify the module has 12V power and that the 3.3V regulator (U5) is outputting 3.3V. The SN65HVD72DR (U3) runs on 3.3V — without it, the transceiver won't function. If the 3.3V rail reads significantly below 3.3V, a back-powered UPDI programmer may be the cause.

## Step 5: Verify Responses Are Correct

Once you get a response, verify:
- Start byte is `0x04` (not `0x02` — that would mean you're reading your own echo).
- End byte is `0x05`.
- Checksum matches: `row ^ col ^ cmd ^ seq_id ^ data_low ^ data_high ^ status`.
- Status byte is `1` (success) or `0` (error — check `data_value` for error code).

## Quick Python Test Script

```python
import serial
import struct
import time

PORT = '/dev/ttyUSB0'  # adjust for your system
ROW = 0
COL = 0

def build_ping(row, col, seq_id=1):
    cmd = 0
    data = 0
    data_low = data & 0xFF
    data_high = (data >> 8) & 0xFF
    checksum = row ^ col ^ cmd ^ seq_id ^ data_low ^ data_high
    return struct.pack('<BBBBBHBB', 0x02, row, col, seq_id, cmd, data, checksum, 0x03)

ser = serial.Serial(PORT, 9600, timeout=1)
ser.reset_input_buffer()
time.sleep(0.1)

packet = build_ping(ROW, COL)
print(f"Sending: {packet.hex(' ')}")
ser.write(packet)

time.sleep(0.5)
response = ser.read(ser.in_waiting or 19)
print(f"Received: {response.hex(' ')}")

if len(response) >= 19:
    print("Echo + response detected (dongle echoes)")
    print(f"  Echo:     {response[:9].hex(' ')}")
    print(f"  Response: {response[9:].hex(' ')}")
elif len(response) == 10 and response[0] == 0x04:
    print("Clean response (no echo)")
elif len(response) == 9 and response == packet:
    print("Echo only - module did not respond")
else:
    print(f"Unexpected: {len(response)} bytes")

ser.close()
```
