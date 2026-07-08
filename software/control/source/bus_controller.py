import logging
import struct
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass
from queue import Queue
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
    ModuleInfo
)
from .serial_processor import SerialProcessor

EXAMPLE_INCOMING_MESSAGE = IncomingMessage(
    row=0, column=0, sequence_id=0, command=ModuleCommand.HOME, status=True
)
EXAMPLE_OUTGOING_MESSAGE = OutgoingMessage(row=0, column=0, command=ModuleCommand.HOME)

@dataclass
class BusInfo:
    port: str
    baudrate: int
    num_modules: int
    modules: List[Tuple[int, int]]

class BusController(SerialProcessor):
    """
    Talks to a group of modules that are on a shared bus
    """

    def __init__(
        self,
        port: str,
        modules: Optional[Dict[Tuple[int, int], ModuleController]] = None,
        timeout: int = 2,
        num_retries: int = 3,
        baudrate: int = 19200,
        max_queue_size: int = 64,
    ) -> None:
        super().__init__(
            port,
            baudrate,
            timeout,
            num_retries,
            max_queue_size
        )
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

    def discover(
        self, row_range: List[int], column_range: List[int], timeout: float = 0.05
    ) -> None:
        tmp = self.timeout
        self.timeout = timeout

        self._ensure_valid_discover_args(row_range)
        self._ensure_valid_discover_args(column_range)

        start_time = time.time()
        self.modules = {}
        for row in range(row_range[0], row_range[1]):
            for col in range(column_range[0], column_range[1]):
                if row == 0 or col == 0:
                    self.logger.warning(
                        f"Skipping ({row}, {col}) as it is reserved for broadcasts"
                    )
                    continue
                self.logger.debug(f"Searching for module {(row, col)}")
                command = OutgoingMessage(
                    row=row, column=col, command=ModuleCommand.PING
                )
                future = self._send_message(command)
                try:
                    future.result()
                except TimeoutError:
                    self.logger.warning(f"Timeout at {(row, col)}")
                    continue
                self.modules[(row, col)] = ModuleController(row, col)
                self.modules[(row, col)].register_command_queue(self.queue, self.port)

        self.logger.debug("Waiting for command queue to clear")
        while not self.queue.empty():
            time.sleep(0.1)
        self.timeout = tmp
        self.logger.info(
            f"{len(self.modules)} modules found in {time.time() - start_time:.2f}s!"
        )
        self.logger.info(f"Module Locations: {self.module_locations}")
        return self.module_locations

    def get_module_info(self) -> List[ModuleInfo]:
        info: List[ModuleInfo] = []
        for module in self.modules.values():
            self.logger.debug(vars(module))
            module_info = module.get_module_info()
            self.logger.debug(module_info)
            info.append(module_info)
        return info

    def broadcast(self, command: ModuleCommand, data_value: int = 0) -> None:
        # Send message to ID (0, 0) which all modules will read, but not respond to so we don't overwhelm the bus.
        # Could even do (0, i) to broadcast to a single column or (i, 0) for a whole row
        message = OutgoingMessage(
            row=0, column=0, command=command, data_value=data_value
        )
        future = self._send_message(message)

    def reset_processed_commands(self) -> None:
        self._processed_commands = 0

    def _send_message(self, message: OutgoingMessage) -> Future:
        future = Future()
        self.queue.put((future, message))
        return future

    def _read_serial_response(self) -> bytes:
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
    ) -> IncomingMessage:
        # incoming is the echo packet (bytes) from the Arduino
        if not incoming:
            self.logger.warning(f"No response to {outgoing}")
            return

        try:
            response = IncomingMessage.decode(incoming)
            self.logger.debug(f"Incoming Message: {response}")
        except Exception as e:
            self.logger.error(
                f"Unable to decode incoming message {incoming} - {str(e)}"
            )
            raise e

        if sequence_id != response.sequence_id:
            self.logger.warning(
                f"Sequence ID for incoming - {response.sequence_id} doesn't match outgoing - {sequence_id}"
            )
            self.error_queue(outgoing)

        # Throw error if a non-ping command is trying to be processed on this bus
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

    def _ensure_valid_discover_args(self, val_range: List[int]) -> None:
        if len(val_range) != 2:
            raise ValueError(
                f"Range input was: {val_range}, should be [MIN_VAL, MAX_VAL]"
            )
        for val in val_range:
            if val < 0 or val > 256:
                raise ValueError(
                    f"Discover value must be betweeen 0-{MAX_ROW_VALUE} - Not {val}"
                )

        if not val_range[0] < val_range[1]:
            raise ValueError(f"Range is not increasing - {val_range}")

    @property
    def info(self) -> BusInfo:
        return BusInfo(
            port=self.port,
            baudrate=self.baudrate,
            num_modules=self.num_modules,
            modules=[tuple(location) for location in self.module_locations]
        )

    @property
    def processed_commands(self) -> int:
        return self._processed_commands

    @property
    def module_locations(self) -> List[Tuple[int, int]]:
        return list(self.modules.keys())

    @property
    def num_modules(self) -> int:
        return len(self.modules)
