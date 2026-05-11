import time
import struct
import logging
import serial
import threading
from queue import Queue
from typing import Dict, List, Optional

from .dataclasses_ import IncomingMessage, OutgoingMessage
from .module_controller import ModuleController, ModuleCommand, MAX_MODULE_ID
from .serial_processor import SerialProcessor

EXAMPLE_INCOMING_MESSAGE = IncomingMessage(
    module_id = 0,
    status=True,
    command = ModuleCommand.HOME
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
        bus_port: str,
        bus_id: int,
        modules: Optional[Dict[int, ModuleController]] = None,
        max_queue_size: int = 64,
        baudrate: int = 9600,
        timeout: int = 2
    ) -> None:
        super().__init__(bus_port, baudrate, timeout)
        self.id = bus_id
        self.modules = {} if modules is None else modules
        self.connect()
        
        # Arduino resets when serial port opens - wait for bootloader to finish
        time.sleep(2)

        # Register all modules
        if modules is not None:
            checksum = 0 
            for mod in self.modules.values():
                mod.register_command_queue(self.queue)
                checksum += 1 if mod.is_command_queue_registered else 0
            assert checksum == len(self.modules)
    
    def discover(self, timeout: float = 0.01) -> List[int]:
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

    def _read_serial_response(self) -> IncomingMessage:
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

    def _handle_response(self, incoming: IncomingMessage, outgoing: OutgoingMessage) -> None:
        # incoming is the echo packet (bytes) from the Arduino
        if not incoming:
            self.logger.warning(f"No response to {outgoing}")
            return
        
        try:
            print(incoming)
            self.logger.info(struct.unpack('<BBB?HBB', incoming))
            response = IncomingMessage.decode(incoming)
            self.logger.debug(f"Incoming Message: {response}")
            
            # Log successful command handling
            match echo.command:
                case ModuleCommand.PING:
                    self.logger.debug(f"Module {echo.module_id} found!")
                    if echo.module_id not in self.modules:
                        self.logger.debug(f"Adding module {echo.module_id}")
                        self.modules[echo.module_id] = ModuleController(echo.module_id)
                case _:
                    self.logger.debug(f"Command {echo.command} executed on module {echo.module_id}")
        except Exception as e:
            self.logger.error(f"Failed to decode echo response: {e}")


    @property
    def module_ids(self) -> List[int]:
        if self.num_modules <= 0:
            raise ValueError("No modules currently attached.")
        return list(self.modules.keys())

    @property
    def num_modules(self) -> int:
        return len(self.modules)