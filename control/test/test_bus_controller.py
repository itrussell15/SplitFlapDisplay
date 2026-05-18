import logging
import struct
import sys
import threading
import time
import unittest
from pathlib import Path
from queue import Queue

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

        cls.ROW = 1
        cls.COLUMN = 1
        cls.module = ModuleController(row=cls.ROW, column=cls.COLUMN)
        cls.test_location = (cls.ROW, cls.COLUMN)
        cls.modules = {cls.test_location: cls.module}
        cls.bus = BusController(port=PORT, modules=cls.modules)
        cls.bus.timeout = 0.5

    @classmethod
    def tearDownClass(cls):
        # Runs once after ALL tests in this class
        time.sleep(1)
        self.bus.close()

    def setUp(self):
        self.timeout = 0.5

    def test_ping(self) -> None:
        ping_message = OutgoingMessage(
            row=self.ROW, column=self.COLUMN, command=ModuleCommand.PING
        )
        self.bus.queue.put(ping_message)

        self.wait_for_message_process()
        self.assertEqual(self.bus.processed_commands, 1)
        self.assertTrue(ping_message.is_processed)

    def test_get_steps(self) -> None:
        self.modules[self.test_location].get_steps()
        self.wait_for_message_process()
        self.assertEqual(self.bus.processed_commands, 1) 

    def test_get_position(self) -> None:
        self.modules[self.test_location].get_position(1)
        self.wait_for_message_process()
        self.assertEqual(self.bus.processed_commands, 1)

    def test_move_to_step(self) -> None:
        self.modules[self.test_location].move_to_step(1000)
        self.wait_for_message_process()
        self.assertEqual(self.bus.processed_commands, 1)
        

    def wait_for_message_process(self, message: OutgoingMessage) -> None:
        while not message.is_processed:
            time.sleep(0.05)

    # def test_bad_checksum(self) -> None:
    #     # TODO Update this based on new packet
    #     packet = b'\x02\x01\x06\xff\x00\xff\x03'
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

    # def test_single_command(self) -> None:
    #     self.modules[1].move_to_step(110)

    #     # TODO Check module for updated value

    #     self.modules[1].get_steps()
    #     time.sleep(SLEEP_TIME_S)
    #     self.assertEqual(self.bus.processed_commands, 2)
