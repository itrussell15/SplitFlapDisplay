import logging
import os
import sys
import time
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
print(sys.path)

from control.source.bus_controller import BusController
from control.source.dataclasses_ import IncomingMessage, ModuleCommand, OutgoingMessage
from control.source.display_controller import DisplayController
from control.source.flaps import Flap
from control.source.module_controller import (
    FirmwareException,
    MAX_SPEED,
    ModuleController,
    MOTOR_RESOLUTION,
    NUM_POSITIONS,
)
from utils import create_logger


def main():
    port = os.getenv("DISP_USB_PORT")
    bus = BusController(port=port, timeout=0.75)
    bus.discover([1, 2], [1, 3], 0.1)  # probe columns 1-4 (empty columns just time out)
    display = DisplayController()
    display.add_bus_controller(bus)

    for module in bus.modules.values():
        module.set_calibration_mode(True)
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
            ans = (
                input(
                    f"Is the module {module.location} at the start position? "
                    f"Enter 'y' to accept, or a signed number of steps to move "
                    f"(e.g. 20 or -15): "
                )
                .strip()
                .lower()
            )
            if ans in ("y", "yes"):
                break

            try:
                step_amount = int(ans)
            except ValueError:
                print(f"'{ans}' is not 'y' or a whole number of steps")
                continue

            # The home offset is an absolute step from the hall sensor
            # (0 .. MOTOR_RESOLUTION-1), so clamp the new target into range.
            new_target = step_values[module.location] + step_amount
            new_target = max(0, min(new_target, MOTOR_RESOLUTION - 1))
            step_values[module.location] = new_target

            # The motor only moves forward (wrapping at MOTOR_RESOLUTION), so to
            # reach a LOWER step we re-home first (home offset is 0 during
            # calibration) and then move forward to the new target. Otherwise a
            # small "back up" would spin almost a full revolution.
            if step_amount < 0:
                module.home()
                time.sleep(6.5)
            module.move_to_step(new_target)

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
                print(
                    f"Home offset for {module.location} saved and verified: {verify.data_value}"
                )
                break
            else:
                print(
                    f"Attempt {attempt}: verification failed for {module.location} - wrote {step_values[module.location]}, read back {None if verify is None else verify.data_value}"
                )
                if attempt == max_attempts:
                    print(
                        f"Failed to verify home offset for {module.location} after {max_attempts} attempts"
                    )

    for module in bus.modules.values():
        module.set_calibration_mode(False)


if __name__ == "__main__":
    create_logger()
    main()
