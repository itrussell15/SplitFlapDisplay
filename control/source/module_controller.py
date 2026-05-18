import enum
import logging
import struct
from queue import Queue
from concurrent.futures import Future
from typing import Any, Optional, Tuple

from .dataclasses_ import IncomingMessage, ModuleCommand, OutgoingMessage

MOTOR_RESOLUTION = 4096
MAX_SPEED = 10
NUM_POSITIONS = 64

MIN_ROW_VALUE = 0
MAX_ROW_VALUE = 255
MIN_COLUMN_VALUE = 0
MAX_COLUMN_VALUE = 255


class ModuleController:
    """
    Generates commands and tracks the state of a given module.
    """

    def __init__(self, row: int, column: int) -> None:
        self.logger = logging.getLogger(f"{self.__class__.__name__}({row}, {column})")
        self.logger.debug(f"Module at ({row}, {column}) created")

        if row < MIN_ROW_VALUE or row > MAX_ROW_VALUE:
            raise ValueError(
                f"Row {row} not allowed. Must be {MIN_ROW_VALUE} <= x <= {MAX_ROW_VALUE}"
            )
        if column < MIN_COLUMN_VALUE or column > MAX_COLUMN_VALUE:
            raise ValueError(
                f"Column {column} not allowed. Must be {MIN_COLUMN_VALUE} <= x <= {MAX_COLUMN_VALUE}"
            )

        self._location = (row, column)
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
        return self._send_packet(ModuleCommand.MOVE_TO_STEP, step)

    def get_steps(self) -> int:
        result = self._send_packet(ModuleCommand.GET_STEPS)
        return result

    def move_to_position(self, position: int) -> None:
        # Move to a stored EEPROM position
        if not self.is_valid_position(position):
            raise ValueError(
                f"Step value: {position} must be between 0-{MOTOR_RESOLUTION}"
            )
        return self._send_packet(ModuleCommand.MOVE_TO_POSITION, value=position)

    def set_position(self, position: int) -> None:
        # Update the motors steps in EEPROM position to current location
        if not self.is_valid_position(position):
            raise ValueError(
                f"Step value: {position} must be between 0-{MOTOR_RESOLUTION}"
            )

    def get_position(self, position: int) -> None:
        if not self.is_valid_position(position):
            raise ValueError(
                f"Step value: {position} must be between 0-{MOTOR_RESOLUTION}"
            )
        return self._send_packet(ModuleCommand.GET_POSITION, value=position)

    def home(self) -> None:
        self.logger.info(f"Homing")
        output = self._send_packet(ModuleCommand.HOME, wait_for_result=False)
        self.is_homed = True
        return output

    def stop(self) -> None:
        return self._send_packet(ModuleCommand.STOP)

    def set_speed(self, value: int) -> None:
        self.logger.info(f"Setting speed to {value}")
        if not self.is_valid_speed(value):
            raise ValueError(f"Speed value: {value} must be between 0-{MAX_SPEED}")
        return self._send_packet(ModuleCommand.SET_SPEED, value=value)

    def get_speed(self) -> None:
        return self._send_packet(ModuleCommand.GET_SPEED)

    def update(self, message: IncomingMessage) -> None:
        self.logger.info(f"Updating based on {message}")
        # TODO Handle updating

    def _send_packet(
        self, command: ModuleCommand, value: int = 255, add_to_queue: bool = True, wait_for_result: bool = True
    ) -> Optional[IncomingMessage]:
        message = OutgoingMessage(
            row=self.row, column=self.column, command=command, data_value=value
        )
        self.logger.debug(f"Packet generated for message: {message}")
        if add_to_queue:
            if self._command_queue is None:
                raise RuntimeError("No command queue registered")
            future = Future()
            self._command_queue.put((future, message))
        
        return future.result() if wait_for_result else None

    def is_valid_position(self, position_id: int) -> bool:
        return position_id >= 0 and position_id <= NUM_POSITIONS

    def is_valid_step(self, step: int) -> bool:
        return step >= 0 and step <= MOTOR_RESOLUTION

    def is_valid_speed(self, speed: int) -> bool:
        return speed > 0 and speed <= MAX_SPEED

    @property
    def location(self) -> Tuple[int, int]:
        return self._location

    @property
    def row(self) -> int:
        return self._location[0]

    @property
    def column(self) -> int:
        return self._location[1]

    @property
    def is_command_queue_registered(self) -> int:
        return self._command_queue is not None
