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
    port = os.getenv("DISP_USB_PORT")
    bus = BusController(port=port, timeout=0.75)
    bus.discover([1, 2], [1, 10], 0.1)
    display = DisplayController()
    display.add_bus_controller(bus)

    for module in bus.modules.values():
        module.set_calibration_mode(True)
    time.sleep(10)
    for position in range(NUM_POSITIONS):
        print(f"Showing: {Flap(position).name}")
        message = display.move_all_to_position(position)
        time.sleep(1.0)

    for module in bus.modules.values():
        module.set_calibration_mode(False)

if __name__ == "__main__":
    create_logger()
    main()