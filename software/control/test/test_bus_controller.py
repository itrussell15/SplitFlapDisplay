import logging
import struct
import sys
import threading
import time
import unittest
from concurrent.futures import Future
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from source.bus_controller import BusController
from source.dataclasses_ import IncomingMessage, ModuleCommand, OutgoingMessage
from source.module_controller import (
    FirmwareException,
    MAX_SPEED,
    ModuleController,
    MOTOR_RESOLUTION,
    NUM_POSITIONS,
)
from test.mock_components.mock_module_firmware import MockFirmware
from utils import create_logger

MODULE_IDS = [1, 2, 3, 4, 5]
SLEEP_TIME_S = 1.0
PORT = "/dev/ttyUSB0"


class TestBusController(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        create_logger(level=logging.DEBUG, spacing=23)

        cls.ROW = 1
        cls.COLUMN = 1
        cls.module = ModuleController(row=cls.ROW, column=cls.COLUMN)
        cls.test_location = (cls.ROW, cls.COLUMN)
        cls.modules = {cls.test_location: cls.module}
        cls.bus = BusController(port=PORT, modules=cls.modules)
        cls.latencies = []

    @classmethod
    def tearDownClass(cls):
        # Runs once after ALL tests in this class
        cls.bus.close()
        print(f"Average Latency: {sum([i.total for i in cls.latencies]) / len(cls.latencies):.2f}ms")

    def setUp(self):
        self.timeout = 0.5
        self.bus.reset_processed_commands()

    def tearDown(self):
        time.sleep(1.0)
        self.timeout = 0.5

    def test_ping(self) -> None:
        ping_message = OutgoingMessage(
            row=self.ROW, column=self.COLUMN, command=ModuleCommand.PING
        )
        future = Future()
        self.bus.queue.put((future, ping_message))
        response = future.result()
        self.assertEqual(response.command, ModuleCommand.PING)
        self.assertTrue(response.status)

    def test_get_steps(self) -> None:
        message = self.modules[self.test_location].get_steps()
        self.assertEqual(message.command, ModuleCommand.GET_STEPS)
        self.assertTrue(message.status)
        self.latencies.append(message.latency_ms)

    def test_get_speed(self) -> None:
        message = self.modules[self.test_location].get_speed()
        self.assertEqual(message.command, ModuleCommand.GET_SPEED)
        self.assertTrue(message.status)
        self.latencies.append(message.latency_ms)

    def test_move_steps(self) -> None:
        message = self.modules[self.test_location].move_to_step(4000)
        self.assertEqual(message.command, ModuleCommand.MOVE_TO_STEP)
        self.assertTrue(message.status)
        self.latencies.append(message.latency_ms)
        time.sleep(10)
        message = self.modules[self.test_location].get_steps()

        message = self.modules[self.test_location].move_to_step(2000)
        self.assertEqual(message.command, ModuleCommand.MOVE_TO_STEP)
        self.assertTrue(message.status)
        self.latencies.append(message.latency_ms)
        # message = self.modules[self.test_location].move_to_step(1000)
        # self.assertEqual(message.command, ModuleCommand.MOVE_TO_STEP)
        # self.assertTrue(message.status)
        # self.latencies.append(message.latency_ms)

    def test_get_position(self) -> None:
        message = self.modules[self.test_location].get_position(15)
        self.assertEqual(message.command, ModuleCommand.GET_POSITION)
        self.assertTrue(message.status)
        self.latencies.append(message.latency_ms)

    # def test_get_all_positions(self) -> None:
    #     positions = self.modules[self.test_location].get_all_positions()
    #     self.assertEqual(len(positions), NUM_POSITIONS)
    #     self.assertTrue(self.modules[self.test_location].positions_known)
    #     # self.assertEqual(message.command, ModuleCommand.GET_SPEED)
    #     # self.assertTrue(message.status)

    def test_bad_command(self) -> None:
        with self.assertRaises(FirmwareException):
            message = self.modules[self.test_location]._send_packet(
                ModuleCommand.BAD_COMMAND
            )

    # def test_discover(self) -> None:
    #     # Test all bad values
    #     with self.assertRaises(ValueError):
    #         self.bus.discover([0, 5], [0, -1])
    #     with self.assertRaises(ValueError):
    #         self.bus.discover([0, -1], [0, 5])
    #     with self.assertRaises(ValueError):
    #         self.bus.discover([0, 500], [0, 10])
    #     with self.assertRaises(ValueError):
    #         self.bus.discover([0, 4], [0, 500])

    #     # Actually search for 1 module
    #     self.bus.discover([1, 3], [1, 3], 0.1)
    #     self.assertEqual(len(self.bus.modules), 1)

    def test_broadcast(self) -> None:
        self.bus.broadcast(ModuleCommand.MOVE_TO_STEP, 1000)
        self.assertEqual(self.bus.queue.qsize(), 1)

    def test_hall_effect_status(self) -> None:
        message = self.modules[self.test_location].get_hall_effect_status()
        self.assertEqual(message.command, ModuleCommand.GET_HALL_EFFECT_STATUS)
        self.assertTrue(message.status)
        self.latencies.append(message.latency_ms)

    def test_is_moving(self) -> None:
        message = self.modules[self.test_location].is_moving()
        self.assertEqual(message.command, ModuleCommand.IS_MOVING)
        self.assertTrue(message.status)
        self.assertFalse(bool(message.data_value))
        self.latencies.append(message.latency_ms)

        message = self.modules[self.test_location].move_to_step(3000)
        message = self.modules[self.test_location].is_moving()
        self.assertTrue(bool(message.data_value))
        self.latencies.append(message.latency_ms)