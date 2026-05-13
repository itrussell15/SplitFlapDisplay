import enum
from queue import Queue
import struct
import logging
from .dataclasses_ import OutgoingMessage, ModuleCommand

from typing import Any, Optional

MOTOR_RESOLUTION = 4096
MAX_SPEED = 10
MAX_MODULE_ID = 256
NUM_POSITIONS = 64


class ModuleController:
    """
    Generates commands and tracks the state of a given module.
    """
    def __init__(self, module_id: int) -> None:
        self.logger = logging.getLogger(f"{self.__class__.__name__}({module_id})")
        self.logger.debug(f"Module {module_id} created")

        if module_id <= 0 or module_id > 255:
            raise ValueError(f"Module ID {module_id} not allowed. Must be 1 <= x <= 255")

        self._module_id = module_id
        self._command_queue = None
        self._is_homed: bool = False

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
    
    def move_to_step(self, step: int) -> None:
        self.logger.info(f"Moving to {step}")
        if not self.is_valid_step(step):
            raise ValueError(f"Step value: {step} must be between 0-{MOTOR_RESOLUTION}")
        return self._create_packet(ModuleCommand.MOVE_TO_STEP, step)

    def get_steps(self) -> None:
        return self._create_packet(ModuleCommand.GET_STEPS)

    def move_to_position(self, position: int) -> None:
        # Move to a stored EEPROM position
        if not self.is_valid_position(position):
            raise ValueError(f"Step value: {position} must be between 0-{MOTOR_RESOLUTION}")
        return self._create_packet(ModuleCommand.MOVE_TO_POSITION, value=position)

    def set_position(self, position: int) -> None:
        # Update the motors steps in EEPROM position to current location
        if not self.is_valid_position(position):
            raise ValueError(f"Step value: {position} must be between 0-{MOTOR_RESOLUTION}")
        return self._create_packet(ModuleCommand.SET_POSITION, value=position)

    def home(self) -> None:
        self.logger.info(f"Homing")
        output = self._create_packet(ModuleCommand.HOME)
        self.is_homed = True
        return output

    def stop(self) -> None:
        return self._create_packet(ModuleCommand.STOP)

    def set_speed(self, value: int) -> None:
        self.logger.info(f"Setting speed to {value}")
        if not self.is_valid_speed(value):
            raise ValueError(f"Speed value: {value} must be between 0-{MAX_SPEED}")
        return self._create_packet(ModuleCommand.SET_SPEED, value=value)

    def get_speed(self) -> None:
        return self._create_packet(ModuleCommand.GET_SPEED)

    def update(self, message: IncomingMessage) -> None:
        self.logger.info(f"Updating based on {message}")
        # TODO Handle updating

    def _create_packet(self, command: ModuleCommand, value: int = 255, add_to_queue: bool = True) -> OutgoingMessage:
        message = OutgoingMessage(module_id=self.module_id, command=command, data_value=value)
        self.logger.debug(f"Packet generated for message: {message}")
        if add_to_queue:
            if self._command_queue is None:
                raise RuntimeError("No command queue registered")
            self._command_queue.put(message)
        return message

    def is_valid_position(self, position_id: int) -> bool:
        return position_id >= 0 and position_id <= NUM_POSITIONS
    
    def is_valid_step(self, step: int) -> bool:
        return step >= 0 and step <= MOTOR_RESOLUTION

    def is_valid_speed(self, speed: int) -> bool:
        return speed > 0 and speed <= MAX_SPEED

    @property
    def is_command_queue_registered(self) -> int:
        return self._command_queue is not None

    @property
    def module_id(self) -> int:
        return self._module_id