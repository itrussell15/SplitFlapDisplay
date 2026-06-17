import os
import logging
import sys
import time
from random import shuffle
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
    bus = BusController(port=port, timeout=0.25)
    bus.discover([1, 2], [1, 8], 0.1)  # probe columns 1-4 (empty columns just time out)
    display = DisplayController()
    display.add_bus_controller(bus)

    with open(os.path.join(os.path.dirname(__file__), "test_words.txt")) as f:
        words = f.readlines()
    shuffle(words)
    for word in words:
        word = word.strip()
        positions = {}
        for char, module in zip(word, bus.modules.values()):
            positions.update({module.location: Flap[char]})
        display.move_to_flaps(positions)
        print(f"Displaying {word}")
        time.sleep(5)


if __name__ == "__main__":
    create_logger()
    main()