import unittest
import sys
import time
import struct
import threading
import logging
from queue import Queue
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from source.module_controller import (
    ModuleController, MAX_SPEED, MOTOR_RESOLUTION
)
from source.bus_controller import BusController
from source.dataclasses_ import (
    IncomingMessage,
    OutgoingMessage,
    ModuleCommand
)
from source.utils import create_logger
from test.mock_components.mock_module_firmware import MockFirmware

MODULE_IDS = [1, 2, 3, 4, 5]
SLEEP_TIME_S = 0.5
PORT = "/dev/ttyACM0"


class TestModuleController(unittest.TestCase):

    def setUp(self):
        create_logger(level=logging.DEBUG, spacing=23)
        self.module_id = 0
        
        self.modules = {i: ModuleController(i) for i in MODULE_IDS}
        self.bus = BusController(port=PORT, modules=self.modules)
        self.bus.timeout = 0.5
        # self.bus.discover()
        
        # self.firmware = MockFirmware(port="/tmp/vcom_host", module_ids=MODULE_IDS)
        # self.firmware_listening = threading.Thread(target=self.firmware.listen, daemon=True)

        self.bus.processor.start()
        # self.firmware_listening.start()
        
    def tearDown(self):
        # Let processor stop working
        # self.firmware.stop_event.set()
        # self.firmware_listening.join(timeout=1)
        # self.firmware.close()

        self.bus.close()

    def test_single_command(self) -> None:
        self.modules[1].move_to_step(1)
        time.sleep(SLEEP_TIME_S)
        self.assertEqual(self.bus.processed_commands, 1)

    def test_get_position(self) -> None:
        self.modules[1].get_position(1)
        time.sleep(SLEEP_TIME_S)
        self.assertEqual(self.bus.processed_commands, 1)

    def test_bad_checksum(self) -> None:
        packet = b'\x02\x01\x06\xff\x00\xff\x03'
        self.bus.queue.put(packet)
        time.sleep(SLEEP_TIME_S)
        self.assertEqual(self.bus.error_queue.qsize(), 1)
        
        bad_packet = self.bus.error_queue.get()
        self.assertIsInstance(bad_packet, IncomingMessage)
        self.assertFalse(bad_packet.status)
        self.assertEqual(bad_packet.data_value, 1)

    def test_bad_command_id(self) -> None:
        # Sends command ID of 100
        packet = b'\x02\x01\x64\x00\x00\x65\x03'
        self.bus.queue.put(packet)
        time.sleep(SLEEP_TIME_S)
        self.assertEqual(self.bus.error_queue.qsize(), 1)

        bad_packet = self.bus.error_queue.get()
        self.assertIsInstance(bad_packet, bytes)
        self.assertEqual(bad_packet[3], 2)
        
    def test_discover(self) -> None:    
        self.bus.discover(0.01)
        time.sleep(SLEEP_TIME_S)
        self.assertEqual(self.bus.processed_commands, 1)
        self.assertEqual(len(self.bus.modules), 1)

    def test_single_command(self) -> None:
        self.modules[1].move_to_step(110)

        # TODO Check module for updated value

        self.modules[1].get_steps()
        time.sleep(SLEEP_TIME_S)
        self.assertEqual(self.bus.processed_commands, 2)