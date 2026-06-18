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

### Update: 19200 baud → ~16 ms (2026-06)
Raising baud 9600→19200 dropped per-command latency to **~16 ms** (measured; `send`≈0.13 ms
is just the OS buffering the write, `receive`≈16 ms is everything else):
```
 command TX  9 × (10/19200)  ≈ 4.7 ms
 DE pre-delay   delay(5)      ≈ 5.0 ms   ← FIXED — does not shrink with baud
 reply TX   10 × (10/19200)  ≈ 5.2 ms
 overhead                     ≈ ~1.4 ms  → ~16.3 ms
```
**Key insight:** baud only shrinks the byte times; the `delay(5)` DE pre-delay is a fixed
floor (now ~31% of the latency vs ~17% at 9600). So everything asymptotes toward
(DE delay + overhead) unless you also cut the DE delay. Projected per-command latency:

| baud | DE delay = 5 ms | DE delay = 1 ms |
|---|---|---|
| 19200 | ~16 ms (measured) | ~12 ms |
| 38400 | ~11 ms | ~7 ms |
| 57600 | ~10 ms | ~6 ms |
| 115200 | ~8 ms | ~4 ms |

Baud is limited by `SoftwareSerial`, not the transceiver. Test each step with
`test/test_comm.py` (`--interleave` AND while a module is stepping — bit-banged RX is
timing-sensitive and shares the CPU with the step loop); confirm 0 corrupt/dropped
frames. 19200 verified; 38400 likely OK; 57600+ on SoftwareSerial/AVR often gets flaky.
Firmware (`rs485.begin`) and controller (`baudrate`) must match.

### DE delays reduced 5→3 ms (2026-06)
`SendSerialResponse()` delays trimmed to `delay(3)` each. Note which one matters where:
- **Pre-delay** (DE HIGH → before `write`): *inside* the measured round-trip latency.
  5→3 ms saves ~2 ms → round-trip ~14 ms at 19200.
- **Post-delay** (after `write` → DE LOW): *not* in the latency (controller already has
  the reply) but holds the bus driven ~3 ms after the last byte; cutting it frees the
  bus sooner, which matters with no inter-command guard / fire-and-forget.

⚠️ The pre-delay must still cover the dongle's TX→RX switch. If too short, the **first
reply byte is lost** → shows as `CLIPPED_HEAD` in `test/test_comm.py`. Verify before
trusting a lower value.

## Fire-and-forget: full-repaint projection

A fire-and-forget move sends only the 9-byte command (no reply, no `SendSerialResponse`,
so the DE delays don't apply). A full 45-module repaint is then just the command stream:

```
45 modules × 9 bytes = 405 bytes
@ 19200 (0.52 ms/byte):  405 × 0.52 ≈ 211 ms
```

| baud | full repaint (405 bytes) |
|---|---|
| 9600 | ~0.42 s |
| 19200 | **~0.21 s** |
| 38400 | ~0.11 s |
| 115200 | ~0.035 s |

vs the current round-trip repaint of `45 × ~16 ms ≈ 0.72 s` → **~3.4× faster** at 19200.

Practical notes:
- Add a small inter-command spacing (~2 ms) as insurance against overflowing a module's
  64-byte SoftwareSerial RX buffer → realistically ~0.2–0.35 s @ 19200. Should be modest:
  at repaint start modules are idle/draining RX, and moves are non-blocking so a module
  keeps reading RX between steps. Bytes a module drops *while stepping* are other modules'
  commands it doesn't need.
- No replies = no bus contention, which is what makes tight streaming safe.
- Trade: no per-command confirmation — rely on the checksum + an occasional
  `GET_STEPS`/`PING` verification sweep.
- **Bulk/broadcast** (one ~50-byte frame) would be ~26 ms @ 19200 — even faster, but a
  bigger firmware change (length-prefixed framing, no per-module ACK).

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
