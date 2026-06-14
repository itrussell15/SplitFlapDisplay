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

    # Home to get everything in the right place
    display.home_all()

    flap = Flap[input("What flap are you start at? - ")]
    init_step_value = int(input(f"Starting step value for {flap.name}? - "))
    step_values = {location: init_step_value for location in bus.modules}

    display.move_to_steps(step_values)
    for position in range(flap.value, NUM_POSITIONS):
        flap = Flap(position)
        done_mask = {location: False for location in bus.modules}
        while not all(done_mask.values()):
            display.move_to_steps(step_values)
            for location, module in bus.modules.items():
                if done_mask[location]:
                    continue
                correct = input(f"Is module {location} at (pos{position}) {flap.name}? [y/n] - ").strip().lower() == "y"
                done_mask[location] = correct
                if correct:
                    module.set_position(flap.value)
                else:
                    step_values[location] = (step_values[location] + small_adjust) % MOTOR_RESOLUTION

                print(f"Moving {location} {move_offset} steps - Current Step: {step_values[location]}")
        step_values = {location: (value + move_offset) % MOTOR_RESOLUTION for (location, value) in step_values.items()}

if __name__ == "__main__":
    create_logger()
    main()
