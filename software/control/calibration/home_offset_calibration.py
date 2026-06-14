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
    bus.discover([1, 2], [5, 6], 0.1)  # probe columns 1-4 (empty columns just time out)
    display = DisplayController()
    display.add_bus_controller(bus)

    for module in bus.modules.values():
        # Set home offset to 0 before homing
        module.set_home_offset(0)

    # Home to get everything in the right place
    display.home_all()

    time.sleep(5)

    start_value = int(input("Initial Step value guess? - "))
    display.move_all_to_step(start_value)
    step_values = {location: start_value for location in bus.modules}

    for module in bus.modules.values():
        # Per-module interactive calibration loop
        while True:
            module.move_to_step(step_values[module.location])
            ans = input(f"Is the module {module.location} at the start position? [y/n] - ").strip().lower()
            if ans in ("y", "yes"):
                break
            # advance and try again
            step_values[module.location] += move_offset

        # Write the home offset and verify it was saved in EEPROM
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                resp = module.set_home_offset(step_values[module.location])
            except Exception as e:
                print(f"Error setting home offset for {module.location}: {e}")
                resp = None

            # small delay to give EEPROM write a moment
            time.sleep(0.1)

            try:
                verify = module.get_home_offset()
            except Exception as e:
                print(f"Error reading back home offset for {module.location}: {e}")
                verify = None

            if verify is not None and verify.data_value == step_values[module.location]:
                print(f"Home offset for {module.location} saved and verified: {verify.data_value}")
                break
            else:
                print(
                    f"Attempt {attempt}: verification failed for {module.location} - wrote {step_values[module.location]}, read back {None if verify is None else verify.data_value}"
                )
                if attempt == max_attempts:
                    print(f"Failed to verify home offset for {module.location} after {max_attempts} attempts")

if __name__ == "__main__":
    create_logger()
    main()