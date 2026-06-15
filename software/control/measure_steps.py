"""Measure steps-per-revolution by exercising the motor (CMD_MOTOR_NUM_STEPS).

The firmware homes to the raw hall sensor, then counts steps for one full
rotation back to the hall. That measurement BLOCKS the module for several
seconds (home + ~one revolution at ~1 ms/step), so this runner uses a long
read timeout — the normal 0.75-2 s bus timeout would expire and retry,
re-triggering the measurement forever.

Usage:
    python measure_steps.py --port /dev/ttyUSB1 --addresses 1,1 1,2 1,4
    python measure_steps.py --port /dev/ttyUSB1 --addresses 1,1 --timeout 15 --repeat 3
"""

import argparse
from typing import List, Tuple

from source.bus_controller import BusController
from source.module_controller import ModuleController


def measure(port: str, addresses: List[Tuple[int, int]], timeout: float, repeat: int):
    modules = {addr: ModuleController(*addr) for addr in addresses}
    # Long timeout: the firmware can't reply until the full-rotation count is done.
    bus = BusController(port=port, modules=modules, timeout=timeout)
    try:
        for addr in addresses:
            mod = bus.modules[addr]
            counts = []
            for _ in range(repeat):
                counts.append(mod.get_drum_steps().data_value)
            avg = sum(counts) / len(counts)
            spread = max(counts) - min(counts) if len(counts) > 1 else 0
            print(f"Module {addr}: steps/rev = {counts}  (avg {avg:.1f}, spread {spread})")
            print(f"   expected ~4096; large spread => lost steps (friction/speed)")
    finally:
        bus.close()


def _parse_addr(s: str) -> Tuple[int, int]:
    r, c = s.split(",")
    return (int(r), int(c))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", required=True)
    p.add_argument("--addresses", nargs="+", default=["1,1"],
                   help="space-separated row,col pairs, e.g. 1,1 1,2 1,4")
    p.add_argument("--timeout", type=float, default=12.0,
                   help="read timeout per command (s); must exceed the measurement time")
    p.add_argument("--repeat", type=int, default=1,
                   help="measurements per module (repeat to gauge consistency)")
    args = p.parse_args()

    measure(args.port, [_parse_addr(a) for a in args.addresses],
            args.timeout, args.repeat)
