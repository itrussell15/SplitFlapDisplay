# Debugging intermittent module responses (binary protocol)

Symptom: a **single** module is reliable, but with **multiple** modules on the bus
some respond only "every other test." Path: `drive_firmware/` + `software/control/`.

## Leading hypothesis: stale-echo desync (no input-buffer flush)

The USB-RS485 dongle echoes every TX. `read_packet()`
(`control/source/serial_processor.py`) only consumes bytes once
`in_waiting >= size (10)`.

- **Module replies:** buffer holds echo (9) + reply (10) = 19 bytes. The scan walks
  past the echo, finds the real `0x04`, frames correctly, and drains the buffer.
  With one always-answering module this happens every cycle → reliable.
- **Module does NOT reply (or replies late):** only the 9 echo bytes are buffered.
  `in_waiting` never reaches 10, `read_packet` times out **without consuming the
  echo**. Those 9 stale bytes stay in the OS buffer; the next command's echo stacks
  on top and shifts framing → every later reply is misframed or attributed to the
  wrong module (`location not in module_locations` → `return None` →
  `module_controller.py` raises). **One missed reply desyncs everything after it.**

There is no `reset_input_buffer()` before a send anywhere, so the stream never
recovers mid-run. More modules → higher chance one probe misses → desync on some
runs and not others → "every other test."

### Compounding framing bug (`0x04` false-sync)

`read_packet` treats **any** `0x04` as the start byte. The echoed command contains
the **column**, **sequence_id**, and **checksum** bytes, so a module at **column 4**,
any command landing on **`sequence_id == 4`** (rotates 0→255), or a checksum of
`0x04` will false-sync inside the echo and misframe even with no timeout.

## Evidence from `discover_logs.txt`

- `(1,1)` replies cleanly; `(1,2)` times out; everything after is jumbled.
- `(1,5)` physically answered but was still dropped.
- `sequence_id` never advances past 1 across the timed-out probes — the
  "counters only advance on success" bug (`serial_processor.py` `task_done()` /
  `sequence_id += 1` are inside the `try`, not a `finally`).
- NOTE: this log predates the producer-side-timeout fix, but the byte-stream
  problem above is still present in current code.

## Diagnostic steps (no behavior change)

1. **Add instrumentation (logging only):**
   - In `SerialProcessor.worker()`, right after `future, item = self.queue.get()`:
     ```python
     self.logger.debug(f"in_waiting before send: {self.connection.in_waiting}")
     ```
   - In `read_packet`, count and log how many bytes were discarded before the start
     byte was found, and what they were.
   - After a run, print `self.bad_packets`.

2. **Run a repeatable per-module PING loop** (not `discover`, which scans dead
   addresses and muddies the picture): ping each *known* module ~50× in a row and
   tally success/failure **per module** and **per `sequence_id`**.

3. **Read the result against this table:**

   | Observation | Confirms |
   |---|---|
   | `in_waiting` > 0 (typically 9) before a send; failures cascade after the first miss | stale-echo desync (no flush) — the main one |
   | Failures cluster on `sequence_id == 4`, or always hit the column-4 module | `0x04` false-sync framing bug |
   | Genuine `TimeoutError` with `in_waiting == 0` (module truly silent) | firmware turnaround timing (`SendSerialResponse` 5 ms vs v6's 50/10/100 ms) or a blocking op |
   | Only one address ever answers despite multiple modules wired | duplicate `(1,3)` address from hardcoded `setup()` |

4. **Confirm how addresses are set.** `drive_firmware.ino` hardcodes `(1,3)` and
   overwrites EEPROM on every boot, ignoring `flash_eeprom` and the unused
   `getModuleRow()/getModuleColumn()`. If the same `.ino` is flashed to every module
   without editing those constants per build, they all collide on `(1,3)`.

## Candidate fixes (once root cause is confirmed)

- **Flush before each command:** `self.connection.reset_input_buffer()` at the top
  of each `worker()` iteration before TX (kills the stale-echo cascade).
- **Robust framing:** sync to the start byte gated on `in_waiting > 0` (not
  `>= size`), then `connection.read(size - 1)` and validate length. If switching to
  `connection.read(n)`, also make the `timeout` setter propagate to
  `self.connection.timeout`.
- **Move `task_done()` / `sequence_id += 1` into a `finally`** so a failed command
  doesn't stall the queue or mis-pair a late reply.
- **Fix `bus_controller._handle_response`:** `self.error_queue(outgoing)` should be
  `.put(...)` (it's a `Queue`, not callable).
- **Firmware turnaround:** bring `SendSerialResponse` delays in line with the
  working v6 timing (~50 ms before DE HIGH, ~10 ms after, ~100 ms before DE LOW).
- **Firmware HOME:** reply first, home non-blocking in `loop()` (like `targetStep`),
  and remove the duplicate `motor.home()` in `performMessageAction`.
- **Per-module addressing:** read row/column from EEPROM via
  `getModuleRow()/getModuleColumn()` instead of hardcoding and rewriting every boot.
</content>
</invoke>
