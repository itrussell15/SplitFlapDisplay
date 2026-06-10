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
from control.source.module_controller import MAX_SPEED, ModuleController, MOTOR_RESOLUTION, FirmwareException
from utils import create_logger

def main():
    move_offset = 50
    port = os.getenv("DISP_USB_PORT")
    bus = BusController(port=port, timeout=0.75)
    bus.discover([1, 2], [1, 10], 0.1)
    display = DisplayController()
    display.add_bus_controller(bus)

    while True:
        flap = Flap[input("What flap are you calibrating? - ")]
        step_value = int(input(f"Starting step value for {flap.name}? - "))
        done_mask = {location: False for location in bus.modules}
        display.move_all_to_step(step_value)
        while not all(done_mask.values()):
            for location, module in bus.modules.items():
                if done_mask[location]:
                    continue
                module.move_to_step(step_value)    
                correct = input(f"Is module {location} at the desired position? [y/n] - ").strip().lower() == "y"
                done_mask[location] = correct
                if correct:
                    module.set_position(flap.value)
            step_value += move_offset
            print(f"Moving {move_offset} steps - Current Step: {step_value}")
            






if __name__ == "__main__":
    create_logger()
    main()