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
from source.dataclasses_ import IncomingMessage, ModuleCommand, OutgoingMessage
from source.module_controller import MAX_SPEED, ModuleController, MOTOR_RESOLUTION
from source.utils import create_logger
from test.mock_components.mock_module_firmware import MockFirmware

MODULE_IDS = [1, 2, 3, 4, 5]
SLEEP_TIME_S = 1.0
PORT = "/dev/ttyACM0"


class TestBusController(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        create_logger(level=logging.DEBUG, spacing=23)

        cls.ROW = 0
        cls.COLUMN = 0
        cls.module = ModuleController(row=cls.ROW, column=cls.COLUMN)
        cls.test_location = (cls.ROW, cls.COLUMN)
        cls.modules = {cls.test_location: cls.module}
        cls.bus = BusController(port=PORT, modules=cls.modules)

    @classmethod
    def tearDownClass(cls):
        # Runs once after ALL tests in this class
        cls.bus.close()

    def setUp(self):
        self.timeout = 0.5
        self._num_processed_start = self.bus.processed_commands
    
    def tearDown(self):
        time.sleep(0.5)
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

    def test_get_speed(self) -> None:
        message = self.modules[self.test_location].get_speed()
        self.assertEqual(message.command, ModuleCommand.GET_SPEED)
        self.assertTrue(message.status)

    def test_move_steps(self) -> None:
        message = self.modules[self.test_location].move_to_step(100)
        self.assertEqual(message.command, ModuleCommand.MOVE_TO_STEP)
        self.assertTrue(message.status)

    def test_get_position(self) -> None:
        message = self.modules[self.test_location].get_position(15)
        self.assertEqual(message.command, ModuleCommand.GET_POSITION)
        self.assertTrue(message.status)

    def test_discover(self) -> None:
        self.bus.discover()

    # def test_steps(self) -> None:
    #     step_value = 500
    #     message = self.modules[self.test_location].move_to_step(step_value)
    #     self.assertEqual(message.command, ModuleCommand.MOVE_TO_STEP)
    #     real_value = -1
    #     while real_value != step_value:
    #         message = self.modules[self.test_location].get_steps()
    #         real_value = message.data_value
    #         time.sleep(0.1)
    #     self.assertEqual(message.data_value, step_value)

    # def test_get_position(self) -> None:
    #     self.modules[self.test_location].get_position(1)
    #     time.sleep(0.5)
    #     self.assertEqual(self.bus.processed_commands, 1)

    # def test_move_to_step(self) -> None:
    #     self.modules[self.test_location].move_to_step(100)
    #     time.sleep(0.5)
    #     self.assertEqual(self.bus.processed_commands, self._num_processed_start + 1)

    # def test_move_to_position(self) -> None:
    #     self.modules[self.test_location].move_to_position(5)
    #     time.sleep(0.5)
    #     self.assertEqual(self.bus.processed_commands, self._num_processed_start + 1)

    # def test_get_position(self) -> None:
    #     self.modules[self.test_location].get_position(5)
    #     time.sleep(0.5)
    #     self.assertEqual(self.bus.processed_commands, self._num_processed_start + 1)
    
    # def test_double_move(self) -> None:
    #     self.modules[self.test_location].move_to_step(200)
    #     time.sleep(2.0)
    #     self.assertEqual(self.bus.processed_commands, self._num_processed_start + 1)
        
    #     self.modules[self.test_location].move_to_step(1500)
    #     time.sleep(0.5)
    #     self.assertEqual(self.bus.processed_commands, self._num_processed_start + 2)

    # def test_bad_checksum(self) -> None:
    #     # TODO Update this based on new packet
    #     packet = b'\x02\x00\x00\x01\t\xdc\x05\xd1\x03'
    #     self.bus.queue.put(packet)
    #     time.sleep(SLEEP_TIME_S)
    #     self.assertEqual(self.bus.error_queue.qsize(), 1)

    #     bad_packet = self.bus.error_queue.get()
    #     self.assertIsInstance(bad_packet, IncomingMessage)
    #     self.assertFalse(bad_packet.status)
    #     self.assertEqual(bad_packet.data_value, 1)

    # def test_bad_command_id(self) -> None:
    #     # TODO Update this based on new packet
    #     # Sends command ID of 100
    #     packet = b'\x02\x01\x64\x00\x00\x65\x03'
    #     self.bus.queue.put(packet)
    #     time.sleep(SLEEP_TIME_S)
    #     self.assertEqual(self.bus.error_queue.qsize(), 1)

    #     bad_packet = self.bus.error_queue.get()
    #     self.assertIsInstance(bad_packet, bytes)
    #     self.assertEqual(bad_packet[3], 2)

    # def test_discover(self) -> None:
    #     self.bus.discover(0.01)
    #     time.sleep(SLEEP_TIME_S)
    #     self.assertEqual(self.bus.processed_commands, 1)
    #     self.assertEqual(len(self.bus.modules), 1)
