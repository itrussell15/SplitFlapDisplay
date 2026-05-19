import logging
import struct
import threading
import time
from queue import Queue
from concurrent.futures import Future
from typing import Dict, List, Optional, Tuple

import serial

from .dataclasses_ import IncomingMessage, ModuleErrorCodes, OutgoingMessage
from .module_controller import (
    MAX_COLUMN_VALUE,
    MAX_ROW_VALUE,
    MIN_COLUMN_VALUE,
    MIN_ROW_VALUE,
    ModuleCommand,
    ModuleController,
)
from .serial_processor import SerialProcessor

EXAMPLE_INCOMING_MESSAGE = IncomingMessage(
    row=0, column=0, sequence_id=0, command=ModuleCommand.HOME, status=True
)
EXAMPLE_OUTGOING_MESSAGE = OutgoingMessage(row=0, column=0, command=ModuleCommand.HOME)

BUS_SLEEP_TIME_MS = 1


class BusController(SerialProcessor):
    """
    Talks to a group of modules that are on a shared bus
    """

    def __init__(
        self,
        port: str,
        modules: Optional[Dict[Tuple[int, int], ModuleController]] = None,
        max_queue_size: int = 64,
        baudrate: int = 9600,
        timeout: int = 2,
    ) -> None:
        super().__init__(port, baudrate, timeout, max_queue_size)
        self.modules = {} if modules is None else modules
        self.error_queue = Queue()
        self._processed_commands = 0
        self.connect()

        # Arduino resets when serial port opens - wait for bootloader to finish
        time.sleep(1.0)

        # Register all modules
        if modules is not None:
            checksum = 0
            for mod in self.modules.values():
                mod.register_command_queue(self.queue)
                checksum += 1 if mod.is_command_queue_registered else 0
            assert checksum == len(self.modules)

        self.processor = self.start_processor()

    def discover(self, max_row_value: int, max_column_value: int, timeout: float = 0.05) -> None:
        tmp = self.timeout
        self.timeout = timeout

        if max_row_value < 0 or max_row_value > MAX_ROW_VALUE:
            raise ValueError(f"Discover row value must be betweeen 0-{MAX_ROW_VALUE} - Not {max_row_value}")

        if max_column_value < 0 or max_column_value > MAX_COLUMN_VALUE:
            raise ValueError(f"Discover column value must be betweeen 0-{MAX_COLUMN_VALUE} - Not {max_column_value}") 

        start_time = time.time()
        self.modules = {}
        for row in range(0, max_row_value):
            for col in range(0, max_column_value):
                self.logger.debug(f"Searching for module {(row, col)}")
                command = OutgoingMessage(
                    row=row, column=col, command=ModuleCommand.PING
                )
                future = self._send_message(command)
                try:
                    future.result(self.timeout)
                except TimeoutError:
                    continue
                self.modules[(row, col)] = ModuleController(row, col)

        self.logger.debug("Waiting for command queue to clear")
        while not self.queue.empty():
            time.sleep(0.1)
        self.timeout = tmp
        self.logger.info(f"{len(self.modules)} modules found in {time.time() - start_time:.2f}s!")
        self.logger.info(f"Module Locations: {self.module_locations}")

    def broadcast(self, command: ModuleCommand, data_value: int = 0) -> None:
        # Send message to ID (0, 0) which all modules will read, but not respond to so we don't overwhelm the bus.
        # Could even do (0, i) to broadcast to a single column or (i, 0) for a whole row
        message = OutgoingMessage(
            row=0, 
            column=0,
            command=command,
            data_value=data_value
        )
        future = self._send_message(message)
        
    def _send_message(self, message: OutgoingMessage) -> Future:
        future = Future()
        self.queue.put((future, message))
        return future

    def _read_serial_response(self) -> bytes:
        # Arduino firmware echoes back the OutgoingMessage (start_value=2, end_value=3)
        # Poll for data instead of waiting a fixed time
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            if self.connection.in_waiting > 0:
                # Data arrived, start reading immediately
                break
            time.sleep(BUS_SLEEP_TIME_MS / 1000)  # Small sleep to not overwhelm the bus

        incoming_packet = self.read_packet(
            start_value=struct.pack("B", EXAMPLE_INCOMING_MESSAGE.start_value),
            end_value=struct.pack("B", EXAMPLE_INCOMING_MESSAGE.end_value),
            size=EXAMPLE_INCOMING_MESSAGE.packet_size,
        )
        if not incoming_packet:
            self.logger.warning("No response")
            return None
        return incoming_packet

    def _handle_response(
        self, incoming: bytes, outgoing: OutgoingMessage, sequence_id: int
    ) -> None:
        # incoming is the echo packet (bytes) from the Arduino
        if not incoming:
            self.logger.warning(f"No response to {outgoing}")
            return

        try:
            response = IncomingMessage.decode(incoming)
            self.logger.debug(f"Incoming Message: {response}")
        except Exception as e:
            self.logger.error(f"Unable to decode incoming message {incoming} - {str(e)}")
            raise e

        if sequence_id != response.sequence_id:
            self.logger.warning(
                f"Sequence ID for incoming - {response.sequence_id} doesn't match outgoing - {sequence_id}"
            )
            self.error_queue(outgoing)

        checksum = IncomingMessage.checksum(
            response.data_value,
            response.command.value,
            response.row,
            response.column,
            response.status,
            response.sequence_id
        )

        if (
            response.command != ModuleCommand.PING
            and response.location not in self.module_locations
        ):
            self.logger.warning(
                f"Module Recieved - {response.location} is a not known module for this bus"
            )
            self.error_queue.put(response)
            return

        self._processed_commands += 1
        return response
        
    @property
    def processed_commands(self) -> int:
        return self._processed_commands

    @property
    def module_locations(self) -> List[int]:
        if self.num_modules <= 0:
            raise ValueError("No modules currently attached.")
        return list(self.modules.keys())

    @property
    def num_modules(self) -> int:
        return len(self.modules)
