import unittest
import sys
import time
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
from source.dataclasses_ import OutgoingMessage, ModuleCommand
from source.utils import create_logger
from test.mock_components.mock_module_firmware import MockFirmware

MODULE_IDS = [1, 2, 3, 4, 5]


class TestModuleController(unittest.TestCase):

    def setUp(self):
        create_logger(level=logging.DEBUG, spacing=23)
        self.module_id = 0
        
        self.modules = {i: ModuleController(i) for i in MODULE_IDS}
        self.bus = BusController("/tmp/vcom_module", 0, modules=self.modules)
        
        self.firmware = MockFirmware(port="/tmp/vcom_host", module_ids=MODULE_IDS)
        self.firmware_listening = threading.Thread(target=self.firmware.listen, daemon=True)

        self.bus.processor.start()
        self.firmware_listening.start()
        
    def tearDown(self):
        # Let processor stop working
        self.firmware.stop_event.set()
        self.firmware_listening.join(timeout=1)
        
        self.firmware.close()
        self.bus.close()

    def test_discover(self) -> None:    
        self.bus.discover()
        self.assertEqual(len(MODULE_IDS), len(self.bus.modules))

    def test_command_queue_draining(self) -> None:
        self.assertEqual(0, self.bus.queue.qsize())
        for controller in self.modules.values():
            controller.move(100)
        while not self.bus.queue.empty():
            time.sleep(0.1)
        self.assertEqual(0, self.bus.queue.qsize())