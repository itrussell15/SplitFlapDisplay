import unittest
import sys
from queue import Queue
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from source.module_controller import (
    ModuleController, MAX_SPEED, MOTOR_RESOLUTION
)
from source.bus_controller import BusController
from source.dataclasses_ import OutgoingMessage, ModuleCommand

class TestModuleController(unittest.TestCase):

    def setUp(self):
        self.module_id = 0
        self.controllers = {i: ModuleController(i) for i in range(0, 5)}
        self.bus = BusController(0, self.controllers)

    def test_sanity(self) -> None:
        for controller in self.controllers.values():
            controller.move(100)
        print(self.bus.commands.qsize())
        self.bus.processor.start()
