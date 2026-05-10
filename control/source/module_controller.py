import enum
from queue import Queue
import struct
import logging
from .dataclasses_ import OutgoingMessage, ModuleCommand

from typing import Any, Optional

MOTOR_RESOLUTION = 4096
MAX_SPEED = 10
MAX_MODULE_ID = 256


class ModuleController:

    def __init__(self, module_id: int) -> None:
        self.logger = logging.getLogger(f"{self.__class__.__name__}({module_id})")
        self.logger.debug(f"Module {module_id} created")
        self._module_id = module_id
        self._command_queue = None

    def register_command_queue(self, queue: Queue) -> None:
        if not isinstance(queue, Queue):
            raise TypeError(f"Type: {type(queue)} is not allowed")
        self.logger.info(f"Command queue registered")
        self._command_queue = queue
    
    def unregister_command_queue(self) -> Queue:
        if self._command_queue is None:
            self.logger.warning("No command queue registered to unregister")
            return 
        queue = self._command_queue
        self._command_queue = None
        self.logger.info(f"Command queue unregistered")
        return queue
    
    def move(self, position: int) -> None:
        self.logger.info(f"Moving to {position}")
        if position > MOTOR_RESOLUTION or position < 0:
            raise ValueError(f"Positional value: {position} must be between 0-{MOTOR_RESOLUTION}")
        return self._create_packet(ModuleCommand.MOVE_TO_POSITION, position)

    def get_position(self) -> None:
        return self._create_packet(ModuleCommand.GET_POSITION)

    def home(self) -> None:
        self.logger.info(f"Homing")
        return self._create_packet(ModuleCommand.HOME)

    def stop(self) -> None:
        return self._create_packet(ModuleCommand.STOP)

    def set_speed(self, value: int) -> None:
        self.logger.info(f"Setting speed to {value}")
        if value < 0 or value > MAX_SPEED:
            raise ValueError(f"Speed value: {value} must be between 0-{MAX_SPEED}")
        return self._create_packet(ModuleCommand.SET_SPEED, value=value)

    def get_speed(self) -> None:
        return self._create_packet(ModuleCommand.GET_SPEED)

    def update(self, message: IncomingMessage) -> None:
        self.logger.info(f"Updating based on {message}")

    def _create_packet(self, command: ModuleCommand, value: int = 255, add_to_queue: bool = True) -> OutgoingMessage:
        message = OutgoingMessage(module_id=self.module_id, command=command, data_value=value)
        self.logger.debug(f"Packet generated for message: {message}")
        if add_to_queue:
            if self._command_queue is None:
                raise RuntimeError("No command queue registered")
            self._command_queue.put(message)
        return message

    @property
    def is_command_queue_registered(self) -> int:
        return self._command_queue is not None

    @property
    def module_id(self) -> int:
        return self._module_id