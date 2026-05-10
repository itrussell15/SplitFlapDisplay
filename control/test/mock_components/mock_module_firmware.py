import sys
import time 
import logging
import queue
import threading
import serial 
import struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from source.dataclasses_ import IncomingMessage, OutgoingMessage
from source.module_controller import ModuleCommand, ModuleController
from source.serial_processor import SerialProcessor
from source.utils import create_logger


EXAMPLE_MESSAGE = OutgoingMessage(1, ModuleCommand.HOME)


class MockFirmware(SerialProcessor):

    def __init__(self, port: str, module_ids: List[int]) -> None:
        super().__init__(port)
        self.connect()
        self.module_ids = module_ids
        self.stop_event = threading.Event()
        self.commands_processed: int = 0

    def _read_serial_response(self) -> IncomingMessage:
        data = self.read_packet(
            struct.pack("B", EXAMPLE_MESSAGE.start_value),
            struct.pack("B", EXAMPLE_MESSAGE.end_value),
            EXAMPLE_MESSAGE.packet_size
        )
        if not data:
            self.logger.warning(f"No message packet was read")
        message = OutgoingMessage.decode(data)
        return message

    def _handle_response(self, incoming: IncomingMessage, outgoing: OutgoingMessage) -> None:
        if message.module_id not in self.module_ids:
            self.logger.warning(f"Incoming message for module {message.module_id} - which is not attached")
            return
        response = IncomingMessage(
            module_id = message.module_id,
            status=True,
            command = message.command
        )
        self.logger.debug(f"Response: {response}")
        self.send(response.encode())

    def listen(self) -> None:
        while not self.stop_event.is_set():
            if (
                self.connection.in_waiting >= EXAMPLE_MESSAGE.packet_size
            ):
                self.logger.debug(f"Waiting: {self.connection.in_waiting}")
                try:
                    data = self.read_packet(
                        struct.pack("B", EXAMPLE_MESSAGE.start_value),
                        struct.pack("B", EXAMPLE_MESSAGE.end_value),
                        EXAMPLE_MESSAGE.packet_size
                    )
                    if data:
                        message = OutgoingMessage.decode(data)
                        self.logger.info(f"Message received: {message}")
                        if message.module_id not in self.module_ids:
                            self.logger.warning(f"Incoming message for module {message.module_id} - which is not attached")
                            continue
                        response = IncomingMessage(
                            module_id = message.module_id,
                            status=True,
                            command = message.command
                        )
                        self.logger.debug(f"Response: {response}")
                        self.send(response.encode())
                except Exception as e:
                    self.logger.error(str(e))
                    raise e

if __name__ == "__main__":

    create_logger()
    Firmware = MockFirmware("/tmp/vcom_host", [1, 2, 3, 4, 5])
    Firmware.listen()
