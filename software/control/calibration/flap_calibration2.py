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
    adjust_values = {
        "a": -20,
        "s": -10,
        "d": 10,
        "f": 20,
    }
    MAX_STEPS = 300
    port = os.getenv("DISP_USB_PORT")
    bus = BusController(port=port, timeout=0.75)
    bus.discover([1, 2], [2, 3], 0.1)  # probe columns 1-4 (empty columns just time out)
    display = DisplayController()
    display.add_bus_controller(bus)

    # tmp = bus.timeout
    # bus.timeout = 6.0
    # message = [module.get_drum_steps() for location, module  in bus.modules.items()]
    bus.timeout = 3.0
    # time.sleep(5)

    # Home to get everything in the right place
    display.home_all()
    time.sleep(8)

    for flap in Flap:
        # if flap.value < 30:
            # continue
        # display.move_all_to_position(flap.value)
        
        print(f"Moving to {flap.name}")
        done_mask = {location: False for location in bus.modules}
        for module in bus.modules.values():
            position_value = module.get_position(flap.value).data_value
            module.move_to_step(position_value)
        while not all(done_mask.values()):
            for location, module in bus.modules.items():
                input_value = input(f"If the module is at {flap.name}, enter y otherwise select an adjustment value {adjust_values}: ").strip().lower()
                if input_value == "y":
                    done_mask[location] = True
                    module.set_position(flap.value)
                else:
                    if input_value not in adjust_values:
                        if input_value.isnumeric() and (int(input_value) > MAX_STEPS or int(input_value) < -MAX_STEPS):
                            print(f"'{input_value}' is not a valid choice")
                            continue
                        else:
                            step_amount = int(input_value)
                    else:
                        step_amount = adjust_values[input_value]
                    current_step = module.get_steps().data_value
                    if step_amount < 0:
                        module.home()
                        time.sleep(6.5)
                    module.move_to_step(current_step + step_amount)


if __name__ == "__main__":
    create_logger()
    main()
