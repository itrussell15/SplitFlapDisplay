import os
import logging
import sys
import time
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
print(sys.path)

from control.source.bus_controller import BusController
from control.source.display_controller import DisplayController
from control.source.dataclasses_ import IncomingMessage, ModuleCommand, OutgoingMessage
from control.source.flaps import Flap
from control.source.module_controller import MAX_SPEED, ModuleController, MOTOR_RESOLUTION, FirmwareException, NUM_POSITIONS
from utils import create_logger

def main():
    move_offset = 25
    small_adjust = 10
    port = os.getenv("DISP_USB_PORT")
    bus = BusController(port=port, timeout=0.75)
    bus.discover([1, 2], [1, 5], 0.1)  # probe columns 1-4 (empty columns just time out)
    display = DisplayController()
    display.add_bus_controller(bus)

    # Home to get everything in the right place
    display.home_all()

    step_values = {location: 0 for location in bus.modules}
    not_at_start = True
    for module in bus.modules.values():
        while not_at_start:
            module.move_to_step(step_values[module.location])
            not_at_start = input("Is the module at the start position? [y/n] - ").strip().lower() == "n"
            if not not_at_start:
                break
            step_values[module.location] += move_offset
        module.set_home_offset()