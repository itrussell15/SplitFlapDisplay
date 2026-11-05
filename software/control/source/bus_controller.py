import tqdm
import logging
import struct
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass, asdict
from queue import Queue
from typing import Dict, List, Optional, Tuple
from tqdm.contrib.logging import logging_redirect_tqdm

import serial

from .dataclasses_ import IncomingMessage, ModuleErrorCodes, OutgoingMessage, LatencyMs
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
from utils import Range

EXAMPLE_INCOMING_MESSAGE = IncomingMessage(
    row=0, column=0, sequence_id=0, command=ModuleCommand.HOME, status=True
)
EXAMPLE_OUTGOING_MESSAGE = OutgoingMessage(row=0, column=0, command=ModuleCommand.HOME)

@dataclass
class BusInfo:
    port: str
    baudrate: int
    num_modules: int
    average_latency_ms: LatencyMs
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
                mod.register_command_queue(self.queue, port)
                checksum += 1 if mod.is_command_queue_registered else 0
            assert checksum == len(self.modules)

        self.processor = self.start_processor()

    def discover(
        self, row_range: Range, column_range: Range, timeout: float = 0.05
    ) -> None:
        tmp = self.timeout
        self.timeout = timeout

        self._ensure_valid_discover_args(row_range)
        self._ensure_valid_discover_args(column_range)

        start_time = time.time()
        self.modules = {}
        total_modules = row_range.delta * column_range.delta
        pbar = tqdm.tqdm(total=total_modules, desc=f"Searching for {total_modules} modules")
        with logging_redirect_tqdm():
            for row in row_range:
                for col in column_range:
                    pbar.update(1)
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
        with logging_redirect_tqdm():
            for module in tqdm.tqdm(self.modules.values(), desc="Fetching Module Info"):
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
            self.error_queue.put(outgoing)

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

    def _ensure_valid_discover_args(self, val_range: Range) -> None:
        for val in [val_range.min, val_range.max]:
            if val < 0 or val > 256:
                raise ValueError(
                    f"Discover value must be betweeen 0-{MAX_ROW_VALUE} - Not {val}"
                )

    @property
    def info(self) -> BusInfo:
        count, average_latency = self.average_latency
        latency_response = asdict(average_latency)
        latency_response["count"] = count
        return BusInfo(
            port=self.port,
            baudrate=self.baudrate,
            num_modules=self.num_modules,
            average_latency_ms=latency_response,
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
