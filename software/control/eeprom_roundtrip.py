"""Confirm EEPROM position save/retrieve (and persistence) on real hardware.

Phase 1 (default) — round-trip:
    Reads the module's current step, SET_POSITIONs it into an index, then
    GET_POSITIONs it back and checks they match. Proves save/retrieve agree.
    Prints the value so you can verify persistence after a power cycle.

Phase 2 — persistence (run after physically power-cycling the module):
    python eeprom_roundtrip.py --port /dev/ttyUSB1 --row 1 --col 1 --check 5 1234
    Re-reads the index and confirms the value survived the reboot. A failure
    here points at the EEPROM being erased on flash (EESAVE fuse) or the
    module rewriting EEPROM on boot.

Usage:
    python eeprom_roundtrip.py --port /dev/ttyUSB1 --row 1 --col 1 --index 5
    python eeprom_roundtrip.py --port /dev/ttyUSB1 --row 1 --col 1 --check 5 1234
"""

import argparse

from source.bus_controller import BusController
from source.module_controller import ModuleController


def make_bus(port, row, col, timeout=2.0):
    modules = {(row, col): ModuleController(row, col)}
    return BusController(port=port, modules=modules, timeout=timeout)


def round_trip(port, row, col, index):
    bus = make_bus(port, row, col)
    mod = bus.modules[(row, col)]
    try:
        current = mod.get_steps().data_value
        print(f"Current step = {current}")

        mod.set_position(index)  # stores current step at `index` in EEPROM
        read_back = mod.get_position(index).data_value
        print(f"SET_POSITION[{index}] = {current} -> GET_POSITION[{index}] = {read_back}")

        if read_back == current:
            print(f"\n✅ Round-trip OK. Now power-cycle the module and run:\n"
                  f"   python eeprom_roundtrip.py --port {port} --row {row} "
                  f"--col {col} --check {index} {current}")
        else:
            print(f"\n❌ MISMATCH: stored {current}, read back {read_back} "
                  f"(save/get addresses disagree?)")
    finally:
        bus.close()


def check_persist(port, row, col, index, expected):
    bus = make_bus(port, row, col)
    mod = bus.modules[(row, col)]
    try:
        value = mod.get_position(index).data_value
        print(f"GET_POSITION[{index}] after reboot = {value} (expected {expected})")
        if value == expected:
            print("\n✅ Persisted across power cycle — EEPROM is correct.")
        else:
            print("\n❌ NOT persisted. Likely the EEPROM was erased on the last "
                  "flash (set 'Save EEPROM: retained' / EESAVE fuse) or the module "
                  "rewrites EEPROM on boot.")
    finally:
        bus.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", required=True)
    p.add_argument("--row", type=int, default=1)
    p.add_argument("--col", type=int, default=1)
    p.add_argument("--index", type=int, default=5, help="EEPROM position index (0-63)")
    p.add_argument("--check", nargs=2, type=int, metavar=("INDEX", "EXPECTED"),
                   help="persistence check after a power cycle")
    args = p.parse_args()

    if args.check:
        check_persist(args.port, args.row, args.col, args.check[0], args.check[1])
    else:
        round_trip(args.port, args.row, args.col, args.index)
