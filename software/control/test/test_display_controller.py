import os
import logging
import struct
import sys
import threading
import time
import unittest
from pathlib import Path
from concurrent.futures import Future

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from source.bus_controller import BusController
from source.display_controller import DisplayController
from source.dataclasses_ import IncomingMessage, ModuleCommand, OutgoingMessage
from source.module_controller import MAX_SPEED, ModuleController, MOTOR_RESOLUTION, FirmwareException
from utils import create_logger

SLEEP_TIME_S = 1.0

class TestDisplayController(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        create_logger(level=logging.DEBUG, spacing=23)

        modules = [
            (1, 1),
            (1, 2),
        ]
        port = os.getenv("DISP_USB_PORT")
        cls.modules = {(row, col): ModuleController(row=row, column=col) for (row, col) in modules}
        cls.bus = BusController(port=port, modules=cls.modules, timeout=0.75)
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

    def test_move_all_position(self) -> None:
        self.display.move_all_to_position(1)
        self.assertEqual(self.display.processed_commands, 1)

    def test_move_to_position(self) -> None:
        self.display.move_to_position(
            {location: 15 for location in self.modules}
        )

    def test_get_all_steps(self) -> None:
        out = self.display.get_all_steps()
        print(out)

    def test_move_all_to_step(self) -> None:
        out = self.display.move_all_to_step(2850)
        print(out)

    def test_move_to_step(self) -> None:
        value = 2800
        steps = {
            (1, 1): value,
            (1, 2): value - 100,
        }
        out = self.display.move_to_steps(steps)
        print(out)

    def test_set_all_position(self) -> None:
        out = self.display.set_all_position_steps(0)
        print(out)

    def test_home_all(self) -> None:
        out = self.display.home_all()
        print(out)

    def test_get_current_positions(self) -> None:
        out = self.display.get_current_positions()
        print(out)
        self.display.move_to_position(
            {location: 15 for location in self.modules}
        )
        out = self.display.get_current_positions()
        print(out)