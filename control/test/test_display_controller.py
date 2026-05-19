import logging
import struct
import sys
import threading
import time
import unittest
from pathlib import Path
from concurrent.futures import Future

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from source.bus_controller import BusController
from source.display_controller import DisplayController
from source.dataclasses_ import IncomingMessage, ModuleCommand, OutgoingMessage
from source.module_controller import MAX_SPEED, ModuleController, MOTOR_RESOLUTION, FirmwareException
from source.utils import create_logger

SLEEP_TIME_S = 1.0
PORT = "/dev/ttyACM0"

class TestDisplayController(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        create_logger(level=logging.DEBUG, spacing=23)

        cls.ROW = 0
        cls.COLUMN = 0
        cls.module = ModuleController(row=cls.ROW, column=cls.COLUMN)
        cls.test_location = (cls.ROW, cls.COLUMN)
        cls.modules = {cls.test_location: cls.module}
        cls.bus = BusController(port=PORT, modules=cls.modules)
        cls.display = DisplayController()
        cls.display.add_bus_controller(cls.bus)

    @classmethod
    def tearDownClass(cls):
        # Runs once after ALL tests in this class
        time.sleep(0.5)
        cls.bus.close()

    def setUp(self):
        self.timeout = 0.5
        self.display.reset_processed_commands()
    
    def tearDown(self):
        time.sleep(0.5)
        self.timeout = 0.5

    def test_discover(self) -> None:
        self.display.discover(5,5)
        self.assertEqual(self.display.num_buses, 1)
        self.assertEqual(self.display.num_modules, 1)
        self.assertEqual(self.display.processed_commands, 1)

    def test_move_all(self) -> None:
        self.display.move_all_to_position(10)
        self.assertEqual(self.display.processed_commands, 1)

    def test_move_to_position(self) -> None:
        self.display.move_to_position(
            {
                (self.ROW, self.COLUMN): 15
            }
        )
        self.assertEqual(self.display.processed_commands, 1)