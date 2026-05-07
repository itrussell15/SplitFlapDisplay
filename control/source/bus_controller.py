import logging
import serial
import threading
from queue import Queue
from typing import Dict, List, Optional

from .dataclasses_ import OutgoingMessage
from .module_controller import ModuleController, ModuleCommand


class BusController:

    def __init__(self, bus_port: str, bus_id: int, modules: Optional[Dict[int, ModuleController]] = None, max_queue_size = 64) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.id = bus_id
        self.modules = {} if modules is None else modules
        self.commands = Queue(maxsize=max_queue_size)
        self.processor = self.create_queue_processor()

        # Register all modules
        if modules is not None:
            checksum = 0 
            for mod in self.modules.values():
                mod.register_command_queue(self.commands)
                checksum += 1 if mod.is_command_queue_registered else 0
            assert checksum == len(self.modules)
    
    def create_queue_processor(self) -> threading.Thread:
        def worker():
            while True:
                item = self.commands.get()
                self.logger.info(f"Processing: {item}")
                self._send_serial_command(item.generate_packet())
                self.commands.task_done()
        return threading.Thread(target=worker, daemon=True)

    def _send_serial_command(self, command: bytes) -> bool:
        pass

    @property
    def module_ids(self) -> List[int]:
        if self.num_modules <= 0:
            raise ValueError("No modules currently attached.")
        return list(self.modules.keys())

    @property
    def num_modules(self) -> int:
        return len(self.modules)