"""RS485 reliability diagnostic for the binary-protocol modules.

Unlike the normal BusController path, this bypasses read_packet()'s framing
entirely. For each PING it dumps the *complete* raw serial buffer after a fixed
settle delay, then classifies what came back. The goal is to find the root
cause of intermittent dropped messages by distinguishing the failure modes:

  OK           - clean 10-byte reply, start 0x04 / end 0x05 / checksum valid
  NO_REPLY     - only the dongle echo came back, the module said nothing
  CLIPPED_HEAD - reply present but its leading byte(s) are missing (no 0x04)
                 -> half-duplex TURNAROUND: dongle not in RX when module talks
  SHORT        - reply starts 0x04 but is truncated (< 10 bytes)
  BAD_CHECKSUM - full 10 bytes but checksum wrong  -> SIGNAL INTEGRITY (noise)
  BAD_END      - full length but end byte != 0x05  -> framing / signal
  NO_ECHO      - the dongle didn't even echo our TX -> controller/dongle/cabling
  GARBAGE      - none of the above

Usage:
    python diagnose_comms.py --port /dev/ttyUSB1
    python diagnose_comms.py --port /dev/ttyUSB1 --addresses 1,1 1,2 1,4 -n 100
    python diagnose_comms.py --port /dev/ttyUSB1 --interleave   # round-robin
"""
import sys
import argparse
import time
from collections import Counter
from typing import List, Optional, Tuple
from pathlib import Path

import serial

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))
print(sys.path)

from source.dataclasses_ import IncomingMessage, ModuleCommand, OutgoingMessage

ECHO_SIZE = 8 + 1  # OutgoingMessage packet_size (9 bytes)
REPLY_SIZE = 10  # IncomingMessage packet_size
REPLY_START = 0x04
REPLY_END = 0x05


def classify(sent: bytes, raw: bytes) -> Tuple[str, Optional[IncomingMessage]]:
    """Classify the raw buffer captured after sending `sent`.

    Some USB-RS485 dongles echo the transmitted bytes back, some do not. We
    handle both: strip the echo if present, otherwise treat the whole buffer
    as the reply.
    """
    if raw.startswith(sent):
        reply = raw[len(sent):]  # dongle echoed our TX; drop it
    else:
        reply = raw              # no echo on this dongle

    if len(reply) == 0:
        return "NO_REPLY", None

    if reply[0] != REPLY_START:
        # Junk before a start byte: leading reply bytes lost (turnaround) or
        # line noise. Find a start byte if there is one.
        idx = reply.find(bytes([REPLY_START]))
        if idx == -1:
            return "GARBAGE", None
        return _classify_reply(reply[idx:], prefix="CLIPPED_HEAD")

    return _classify_reply(reply, prefix=None)


def _classify_reply(reply: bytes, prefix: Optional[str]):
    if len(reply) < REPLY_SIZE:
        return (prefix or "SHORT"), None
    frame = reply[:REPLY_SIZE]
    if frame[-1] != REPLY_END:
        return (prefix or "BAD_END"), None
    try:
        msg = IncomingMessage.decode(frame)
    except Exception:
        return (prefix or "BAD_CHECKSUM"), None
    if prefix:  # head was clipped but tail happened to realign - still suspect
        return prefix, msg
    return "OK", msg


def ping_once(conn: serial.Serial, row: int, col: int, seq: int, settle: float):
    conn.reset_input_buffer()
    sent = OutgoingMessage(
        row=row, column=col, command=ModuleCommand.PING
    ).encode(seq)
    conn.write(sent)
    conn.flush()
    time.sleep(settle)
    raw = conn.read(conn.in_waiting or 1)
    # opportunistically drain anything still trickling in
    time.sleep(0.02)
    if conn.in_waiting:
        raw += conn.read(conn.in_waiting)
    return sent, raw


def run(port: str, addresses: List[Tuple[int, int]], n: int,
        settle: float, interleave: bool):
    conn = serial.Serial(port=port, baudrate=9600, timeout=0.2)
    time.sleep(1.0)  # let the dongle/board settle after open

    results = {addr: Counter() for addr in addresses}
    samples = {addr: [] for addr in addresses}  # keep a few raw failures
    # per-attempt log: failure positions both globally and within each module's
    # own sequence of attempts, so we can see WHEN in the run misses happen.
    fails = {addr: [] for addr in addresses}      # (attempt_idx_for_addr, global_idx)
    attempt_idx = {addr: 0 for addr in addresses}
    timeline = []  # one char per ping, in run order: '.'=OK  'X'=fail

    seq = 0
    order = []
    if interleave:
        for _ in range(n):
            order.extend(addresses)
    else:
        for addr in addresses:
            order.extend([addr] * n)

    for global_idx, (row, col) in enumerate(order):
        addr = (row, col)
        a_idx = attempt_idx[addr]
        attempt_idx[addr] += 1
        sent, raw = ping_once(conn, row, col, seq, settle)
        seq = (seq + 1) % 256
        verdict, _ = classify(sent, raw)
        results[addr][verdict] += 1
        timeline.append("." if verdict == "OK" else "X")
        if verdict != "OK":
            fails[addr].append((a_idx, global_idx))
            if len(samples[addr]) < 5:
                samples[addr].append((sent.hex(" "), raw.hex(" ")))

    conn.close()

    print("\n================ RS485 DIAGNOSTIC SUMMARY ================")
    print(f"port={port}  pings/addr={n}  settle={settle}s  "
          f"mode={'interleaved' if interleave else 'isolated'}\n")
    for addr in addresses:
        c = results[addr]
        total = sum(c.values())
        ok = c.get("OK", 0)
        rate = 100.0 * ok / total if total else 0.0
        print(f"  Module {addr}:  {ok}/{total} OK  ({rate:5.1f}%)")
        for verdict, count in c.most_common():
            if verdict == "OK":
                continue
            print(f"       {verdict:<13} {count}")
        if fails[addr]:
            pos = ", ".join(f"#{a}(g{g})" for a, g in fails[addr])
            print(f"       fail @ attempt(global): {pos}")
        for sent_hex, raw_hex in samples[addr]:
            print(f"         e.g. TX[{sent_hex}]  RX[{raw_hex}]")

    # Whole-run timeline: read left-to-right in send order. In isolated mode
    # the blocks are [addr0 x n][addr1 x n]...; a leading 'X' on each block is
    # the "first ping after switching modules" signature.
    print("\n  Timeline (send order, '.'=OK 'X'=fail):")
    row_w = 50
    for i in range(0, len(timeline), row_w):
        print(f"    g{i:<5} {''.join(timeline[i:i + row_w])}")
    first_attempt_fails = sum(1 for a in addresses for (ai, _) in fails[a] if ai == 0)
    later_fails = sum(len(fails[a]) for a in addresses) - first_attempt_fails
    print(f"\n  First-attempt (post-switch/idle) failures: {first_attempt_fails}"
          f"   |  later failures: {later_fails}")
    print("=========================================================\n")
    print("Interpretation:")
    print("  OK high (>=95%)              -> link is healthy at this settle/cadence")
    print("  NO_REPLY dominant            -> module not replying at all. If these")
    print("                                  cluster on the FIRST ping after a gap or")
    print("                                  module switch, it's a recovery/turnaround")
    print("                                  issue, not corruption. Lower --settle to")
    print("                                  find the cadence where it breaks down.")
    print("  CLIPPED_HEAD/SHORT dominant  -> turnaround timing (firmware DE/TX)")
    print("  BAD_CHECKSUM/BAD_END/GARBAGE -> signal integrity (termination/biasing)")
    print("  Per-module skew (one addr much worse) -> that unit's wiring/stub/connector")


def _parse_addr(s: str) -> Tuple[int, int]:
    r, c = s.split(",")
    return (int(r), int(c))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", required=True)
    p.add_argument("--addresses", nargs="+", default=["1,1", "1,2", "1,4"],
                   help="space-separated row,col pairs, e.g. 1,1 1,2 1,4")
    p.add_argument("-n", type=int, default=50, help="pings per address")
    p.add_argument("--settle", type=float, default=0.25,
                   help="seconds to wait for a reply before reading the buffer")
    p.add_argument("--interleave", action="store_true",
                   help="round-robin across addresses instead of one block each")
    args = p.parse_args()

    run(args.port, [_parse_addr(a) for a in args.addresses],
        args.n, args.settle, args.interleave)

