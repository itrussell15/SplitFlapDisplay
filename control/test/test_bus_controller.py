import unittest
import sys
import time
import logging
from queue import Queue
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from source.module_controller import (
    ModuleController, MAX_SPEED, MOTOR_RESOLUTION
)
from source.bus_controller import BusController
from source.dataclasses_ import OutgoingMessage, ModuleCommand
from source.utils import create_logger

class TestModuleController(unittest.TestCase):

    def setUp(self):
        create_logger(level=logging.DEBUG, spacing=23)
        self.module_id = 0
        self.controllers = {i: ModuleController(i) for i in range(0, 5)}
        self.bus = BusController("/tmp/vcom_module", 0, self.controllers)

    def tearDown(self):
        self.bus.close()

    def test_single_command(self) -> None:    
        self.controllers[0].move(100)
        self.bus.processor.start()
        time.sleep(5)

    # def test_command_queue_draining(self) -> None:
    #     for controller in self.controllers.values():
    #         controller.move(100)
    #     self.assertEqual(len(self.controllers), self.bus.commands.qsize())
    #     self.bus.processor.start()
    #     while not self.bus.commands.empty():
    #         time.sleep(0.1)
    #     self.assertEqual(0, self.bus.commands.qsize())