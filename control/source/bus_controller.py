import time
import struct
import logging
import serial
import threading
from queue import Queue
from typing import Dict, List, Optional

from .dataclasses_ import (
    IncomingMessage,
    ModuleErrorCode,
    OutgoingMessage
)
from .module_controller import ModuleController, ModuleCommand, MAX_MODULE_ID
from .serial_processor import SerialProcessor

EXAMPLE_INCOMING_MESSAGE = IncomingMessage(
    module_id = 0,
    sequence_id = 0,
    command = ModuleCommand.HOME,
    status=True
)

EXAMPLE_OUTGOING_MESSAGE = OutgoingMessage(
    module_id = 0,
    command = ModuleCommand.HOME
)

class BusController(SerialProcessor):
    """
    Talks to a group of modules that are on a shared bus
    """
    def __init__(
        self,
        port: str,
        modules: Optional[Dict[int, ModuleController]] = None,
        max_queue_size: int = 64,
        baudrate: int = 9600,
        timeout: int = 2
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
    
    def discover(self, timeout: float = 0.01) -> None:
        tmp = self.timeout
        self.timeout = timeout

        self.modules = {}
        for i in range(1, 6):
            self.logger.debug(f"Searching for module {i}")
            command = OutgoingMessage(
                module_id=i,
                command=ModuleCommand.PING
            )   
            self.queue.put(command)
        
        self.logger.debug("Waiting for command queue to clear")
        while not self.queue.empty():
            time.sleep(0.1)
        self.timeout = tmp
        self.logger.info(f"{len(self.modules)} modules found!")

    def _read_serial_response(self) -> bytes:
        # Arduino firmware echoes back the OutgoingMessage (start_value=2, end_value=3)
        # Poll for data instead of waiting a fixed time
        max_wait = 1.5
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if self.connection.in_waiting > 0:
                # Data arrived, start reading immediately
                break
            time.sleep(0.05)  # Check every 50ms
        
        incoming_packet = self.read_packet(
            start_value = struct.pack("B", EXAMPLE_INCOMING_MESSAGE.start_value),
            end_value = struct.pack("B", EXAMPLE_INCOMING_MESSAGE.end_value),
            size = EXAMPLE_INCOMING_MESSAGE.packet_size,
        )
        if not incoming_packet:
            self.logger.warning("No response")
            return None
        return incoming_packet

    def _handle_response(self, incoming: bytes, outgoing: OutgoingMessage, sequence_id: int) -> None:
        # incoming is the echo packet (bytes) from the Arduino
        if not incoming:
            self.logger.warning(f"No response to {outgoing}")
            return
        
        try:
            response = IncomingMessage.decode(incoming)
            self.logger.debug(f"Incoming Message: {response}")
        except Exception as e:
            self.logger.error(f"Unable to decode incoming message {incoming}")
            self.error_queue.put(incoming)
            return

        if sequence_id != response.sequence_id:
            self.logger.warning(f"Sequence ID for incoming - {response.sequence_id} doesn't match outgoing - {sequence_id}")
            self.error_queue(outgoing)

        checksum = IncomingMessage.checksum(
            response.data_value,
            response.command.value,
            response.module_id,
            response.status
        )
        self.logger.debug(f"Calculated Checksum: {checksum}")
        
        if not response.status:
            self._handle_bad_status(response)
            return
        
        if response.command != ModuleCommand.PING and response.module_id not in self.module_ids:
            self.logger.warning(f"Module Recieved - {response.module_id} is a not known module for this bus")
            self.error_queue.put(response)
            return

        try:
            match response.command:
                case ModuleCommand.PING:
                    self.logger.debug(f"Module {response.module_id} found!")
                    if response.module_id not in self.modules:
                        self.logger.debug(f"Adding module {response.module_id}")
                        self.modules[response.module_id] = ModuleController(response.module_id)
                case ModuleCommand.GET_STEPS:
                    self.modules[response.module_id].update(response)
                case ModuleCommand.GET_SPEED:
                    self.modules[response.module_id].update(response)
                case ModuleCommand.GET_POSITION:
                    self.modules[response.module_id].update(response)
                case _:
                    self.logger.debug(f"Command {response.command} executed on module {response.module_id}")
            self._processed_commands += 1
        except Exception as e:
            self.error_queue.put(response)
            self.logger.error(f"Failed to decode incoming response: {e}")

    def _handle_bad_status(response: IncomingMessage) -> None:
        try:
            error_code = ModuleErrorCode[response.data_value]
            self.logger.warning(f"Response failed with error code {error_code}")
        except KeyError:
            self.logger.error(f"Response contained unknown error code - {response.data_value}")
        except Exception as e:
            self.logger.error(f"Unknown error occured when reading response")
        self.error_queue.put(response)

    @property
    def processed_commands(self) -> int:
        return self._processed_commands

    @property
    def module_ids(self) -> List[int]:
        if self.num_modules <= 0:
            raise ValueError("No modules currently attached.")
        return list(self.modules.keys())

    @property
    def num_modules(self) -> int:
        return len(self.modules)