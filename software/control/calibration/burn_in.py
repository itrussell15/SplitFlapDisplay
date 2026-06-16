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
    move_offset = 64
    small_adjust = 10
    port = os.getenv("DISP_USB_PORT")
    bus = BusController(port=port, timeout=0.75)
    bus.discover([1, 2], [1, 2], 0.1)  # probe columns 1-4 (empty columns just time out)
    display = DisplayController()
    display.add_bus_controller(bus)

    count = 0
    step_values = {location: 0 for location in bus.modules}
    for i in range(25):
        for module in bus.modules.values():
            print(f"Spin {i}")
            display.home_all()
            time.sleep(11)
            count += 1

if __name__ == "__main__":
    create_logger()
    main()