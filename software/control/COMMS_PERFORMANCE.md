# Binary Protocol — Comms Performance & Speed-Up Options

Reference notes on the speed of the binary RS485 protocol (`firmware/drive_firmware/`
+ `software/control/`), how it compares to the v7 text protocol, and the levers
available to make it faster. Baud is **9600** (1 byte ≈ 1.04 ms, 8N1).

## Measured baseline (2026-06)

- **~29 ms per command** (round-trip: send command → receive reply), measured via
  `LatencyMs.total` in `serial_processor.py`.
- No `command_interval`/inter-command sleep currently in the worker, so 29 ms is the
  effective per-command time.
- **Full 45-module repaint ≈ 45 × 29 ≈ ~1.3 s.**

### Where the 29 ms goes
```
 9-byte command TX        9 × 1.04 ms  ≈  9.4 ms
 firmware DE pre-delay    delay(5)     ≈  5.0 ms   (SendSerialResponse)
 10-byte reply TX         10 × 1.04 ms ≈ 10.4 ms
 Python / read overhead                ≈  ~4 ms
                                        ─────────
                                          ~29 ms
```
Note: the `delay(5)` *after* the reply in `SendSerialResponse()` is not in the 29 ms,
but it holds DE HIGH for ~5 ms after the last reply byte. With no inter-command guard,
the next command can begin while the module is still driving the bus — worth trimming
for correctness as well as speed.

## Payload size: binary vs v7 text

| | Binary (`drive_firmware`) | v7 text (`m38-B`) |
|---|---|---|
| Command (controller→module) | **9 bytes** | ~4–6 bytes |
| Reply (module→controller) | **10 bytes** (every targeted cmd) | none (fire-and-forget) |
| Bytes per flap | **19** | **~5** |
| Round-trip required? | Yes (synchronous, one at a time) | No (stream) |

The binary protocol is **heavier on the wire** (~4× the bytes per flap + a mandatory
reply round-trip). What it buys is **reliability and richness**, not speed: per-command
checksum, sequence IDs, explicit error/status replies, (row,col) addressing, and a
2-byte data field that can command an arbitrary step target (not just a character).

## Speed-up levers (quantified against the 29 ms)

| Change | Per-command | 45-module repaint | Effort |
|---|---|---|---|
| **Current** | 29 ms | ~1.3 s | — |
| Trim firmware DE delays 5→1 ms (×2) | ~25 ms | ~1.1 s | trivial (2 constants) |
| + baud 9600→19200 | ~15 ms | ~0.7 s | easy* |
| Fire-and-forget moves (drop reply) | ~12 ms (TX only) | ~0.5–0.7 s | medium |
| **Bulk / broadcast "set all"** | one ~50-byte frame | **~0.05 s** | bigger |

\* 19200 on `SoftwareSerial` is plausible but must be tested — RX has to keep up while
the CPU is bit-banging motor steps; bytes can be lost mid-move.

### 1. Trim the firmware DE delays — free, do first
In `SendSerialResponse()` (`drive_firmware.ino`), `delay(5)` before and after the
`rs485.write()`. They only need to cover the dongle's TX↔RX switch; drop toward ~1 ms
and re-measure. Removes ~4 ms/command and closes the post-reply bus-contention window.

### 2. Fire-and-forget moves — biggest win short of bulk
Make move commands (`MOVE_TO_STEP`/`MOVE_TO_POSITION`) **not** require an ACK. That
removes the 10-byte reply, the 5 ms DE pre-delay, and the read wait → ~29 ms drops to
~12 ms (command TX only). Keep the checksum for integrity; verify occasionally with an
explicit `GET_STEPS`/`PING` instead of ACKing every move. Reliability trade: no
per-command confirmation, but the resync parser + retry already cover transient loss.
Add a small inter-command spacing so a module mid-step doesn't overflow its 64-byte
SoftwareSerial RX buffer.

### 3. Bulk / broadcast "set all positions" — best for full repaints
Instead of 45 individual 19-byte round-trips, send **one** broadcast frame carrying one
position byte per module (≈ `header + 45 payload + checksum` ≈ 50 bytes), fire-and-forget,
where each module pulls out its own index. ~50 bytes total vs ~855 → **~15–40× faster**
for a full repaint. Caveats:
- Must be **length-prefixed framing** (payload can contain `0x02`/`0x03`, so the
  start/end-byte resync parser won't work for it).
- A 50-byte frame approaches the 64-byte SoftwareSerial RX buffer.
- No per-module ACK. **Per-row broadcasts (15 bytes)** are a safer middle ground.

### 4. Higher baud — secondary, riskiest on SoftwareSerial
9600 is the floor; the SN65HVD72 transceiver does Mbps, the limiter is `SoftwareSerial`.
Try 19200/38400 and test reliability during stepping. The real unlock is moving RS485
onto the **hardware USART** — but on this board the USART pins don't reach the RS485
lines, so it's SoftwareSerial-only until a respin. Via PORTMUX the alt USART0 is on
**PA1/PA2 (the IO2/IO1 header pins)**, so a respin routing RS485 there would allow
115200+ (~12×).

### 5. Send only changed flaps — free, content-dependent
Don't issue a move for a flap already showing the target. No protocol change; cuts
traffic on real content.

## Recommended order
1. Trim DE delays (free, re-measure immediately).
2. Fire-and-forget moves (~halves the 29 ms).
3. Bulk/per-row broadcast (makes per-flap count irrelevant for full repaints).
4. Baud / hardware-USART — save for a board respin.

## Key takeaway
The encoding isn't the bottleneck — the **per-command reply round-trip and turnaround**
are. Removing the ACK and/or batching modules into one broadcast frame are the wins;
baud is secondary and the riskiest given SoftwareSerial.
