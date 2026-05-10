import time
import struct
import logging
import serial
import threading
from queue import Queue
from typing import Dict, List, Optional

from .dataclasses_ import IncomingMessage, OutgoingMessage
from .module_controller import ModuleController, ModuleCommand, MAX_MODULE_ID
from .utils import SerialControl

EXAMPLE_INCOMING_MESSAGE = IncomingMessage(
    module_id = 0,
    status=True,
    command = ModuleCommand.HOME
)

class BusController(SerialControl):

    def __init__(
        self,
        bus_port: str,
        bus_id: int,
        modules: Optional[Dict[int, ModuleController]] = None,
        max_queue_size: int = 64,
        baudrate: int = 9600,
        timeout: int = 1
    ) -> None:
        super().__init__(bus_port, baudrate, timeout)
        self.id = bus_id
        self.modules = {} if modules is None else modules
        self.commands = Queue(maxsize=max_queue_size)
        self.processor = self.create_queue_processor()
        self.connect()

        # Register all modules
        if modules is not None:
            checksum = 0 
            for mod in self.modules.values():
                mod.register_command_queue(self.commands)
                checksum += 1 if mod.is_command_queue_registered else 0
            assert checksum == len(self.modules)
    
    def discover(self, timeout: float = 0.01) -> List[int]:
        tmp = self.timeout
        self.timeout = timeout

        self.modules = {}
        for i in range(1, MAX_MODULE_ID):
            self.logger.debug(f"Searching for module {i}")
            command = OutgoingMessage(
                module_id=i,
                command=ModuleCommand.PING
            )
            self.commands.put(command)
        
        self.logger.debug("Waiting for command queue to clear")
        while not self.commands.empty():
            time.sleep(0.1)
        self.timeout = tmp
        self.logger.info(f"{len(self.modules)} modules found!")

    def create_queue_processor(self) -> threading.Thread:
        def worker():
            while True:
                try:
                    item = self.commands.get()
                    self.logger.info(f"Processing: {item}")
                    self._send_serial_command(item.encode())
                    response = self._read_serial_response()
                    self.logger.info(f"Response: {response}")
                    self._handle_response(response, item)
                    self.commands.task_done()
                except Exception as e:
                    self.logger.error(str(e))
        return threading.Thread(target=worker, daemon=True)

    def _send_serial_command(self, command: bytes) -> bool:
        self.logger.debug(f"Raw packet being sent {command}")
        self.send(command)

    def _read_serial_response(self) -> IncomingMessage:
        incoming_packet = self.read_packet(
            start_value = struct.pack("B", EXAMPLE_INCOMING_MESSAGE.start_value),
            end_value = struct.pack("B", EXAMPLE_INCOMING_MESSAGE.end_value),
            size = EXAMPLE_INCOMING_MESSAGE.packet_size,
        )
        if not incoming_packet:
            self.logger.warning("No message response")
        self.logger.debug(f"Incoming Packet: {incoming_packet}")
        return IncomingMessage.decode(incoming_packet)

    def _handle_response(self, incoming: IncomingMessage, outgoing: OutgoingMessage) -> None:
        if not incoming.status:
            self.logger.warning(f"Response to {outgoing} returned bad status")
            raise ValueError(f"Module response was bad: {incoming}")
        
        match incoming.command:
            case ModuleCommand.PING:
                self.logger.debug(f"Module {incoming.module_id} found!")
                if incoming.module_id not in self.modules:
                    self.logger.debug(f"Adding module {incoming.module_id}")
                    self.modules[incoming.module_id] = ModuleController(incoming.module_id)
            case _:
                print("Everything else!")

        # self.modules[outgoing.module_id].update(incoming)

    def close(self) -> None:
        if not self.commands.empty():
            self.logger.info(f"Waiting for {self.commands.qsize()} commands to complete before closing")
        while not self.commands.empty():
            time.sleep(0.1)
        self.logger.info("Closing serial connection")
        super().close()

    @property
    def module_ids(self) -> List[int]:
        if self.num_modules <= 0:
            raise ValueError("No modules currently attached.")
        return list(self.modules.keys())

    @property
    def num_modules(self) -> int:
        return len(self.modules)