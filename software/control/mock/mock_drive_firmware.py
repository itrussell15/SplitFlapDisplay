import sys
import time 
import logging
import queue
import threading
import serial 
import struct
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
print(sys.path)

from control.source.dataclasses_ import IncomingMessage, OutgoingMessage
from control.source.module_controller import ModuleCommand, ModuleController
from control.source.serial_processor import SerialProcessor
from utils import create_logger

class MockFirmware(SerialProcessor):

    def __init__(self, port: str, module_ids: List[Tuple[int, int]]) -> None:
        super().__init__(port)
        self.connect()
        self.module_ids = module_ids
        self.stop_event = threading.Event()
        self.commands_processed: int = 0

    def _read_serial_response(self) -> IncomingMessage:
        print(f"Heard: {}")

    def _handle_response(self, incoming: IncomingMessage, outgoing: OutgoingMessage) -> None:
        pass

if __name__ == "__main__":

    create_logger()
    Firmware = MockFirmware("/tmp/vcom_firmware", [(1, 1)])
    Firmware.start_processor()
    while Firmware.is_alive:
        try:
            time.sleep(0.1)
        except KeyboardInterrupt:
            Firmware.close()
        except Exception:
            raise e
    Firmware.close()
