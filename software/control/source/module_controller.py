import enum
import logging
import struct
from concurrent.futures import Future
from queue import Queue
from typing import Any, Optional, Tuple

from .dataclasses_ import (
    IncomingMessage,
    ModuleCommand,
    ModuleErrorCodes,
    OutgoingMessage,
)

MOTOR_RESOLUTION = 4096
MAX_SPEED = 10
NUM_POSITIONS = 64

MIN_ROW_VALUE = 0
MAX_ROW_VALUE = 255
MIN_COLUMN_VALUE = 0
MAX_COLUMN_VALUE = 255


class FirmwareException(Exception):
    pass


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
        self._current_step: int = 0
        self._current_position: int = None

        # Have to initialize before calling `get_all_positions` otherwise no positions to request for
        self._positions_to_steps = {i: None for i in range(NUM_POSITIONS)}

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
        result = self._send_packet(ModuleCommand.MOVE_TO_STEP, step)
        self._current_step = result.data_value
        return result

    def get_steps(self) -> int:
        result = self._send_packet(ModuleCommand.GET_STEPS)
        self._current_step = result.data_value
        return result

    def move_to_position(self, position: int) -> None:
        # Move to a stored EEPROM position
        if not self.is_valid_position(position):
            raise ValueError(
                f"Step value: {position} must be between 0-{MOTOR_RESOLUTION}"
            )

        result = self._send_packet(ModuleCommand.MOVE_TO_POSITION, value=position)
        self._current_position = position
        self._current_step = result.data_value
        return result

    def set_position(self, position: int) -> None:
        # Update the motors steps in EEPROM position to current location
        if not self.is_valid_position(position):
            raise ValueError(
                f"Position value: {position} must be between 0-{NUM_POSITIONS}"
            )
        # Check if there is already a position at this location
        return self._send_packet(ModuleCommand.SET_POSITION, value=position)

    def get_position(self, position: int) -> IncomingMessage:
        if not self.is_valid_position(position):
            raise ValueError(
                f"Step value: {position} must be between 0-{MOTOR_RESOLUTION}"
            )
        result = self._send_packet(ModuleCommand.GET_POSITION, value=position)
        self._positions_to_steps[position] = result.data_value
        return result

    def get_all_positions(self) -> Dict[int, int]:
        for position in self._positions_to_steps:
            result = self.get_position(position)
        return self._positions_to_steps

    def home(self) -> None:
        self.logger.info(f"Homing")
        output = self._send_packet(ModuleCommand.HOME)
        self.is_homed = True
        self._current_position = 0
        self._current_step = 0
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

    def is_moving(self) -> None:
        return self._send_packet(ModuleCommand.IS_MOVING)

    def is_valid_position(self, position_id: int) -> bool:
        return position_id >= 0 and position_id <= NUM_POSITIONS

    def is_valid_step(self, step: int) -> bool:
        return step >= 0 and step <= MOTOR_RESOLUTION

    def is_valid_speed(self, speed: int) -> bool:
        return speed > 0 and speed <= MAX_SPEED

    def _send_packet(
        self, command: ModuleCommand, value: int = 0
    ) -> Optional[IncomingMessage]:
        message = OutgoingMessage(
            row=self.row, column=self.column, command=command, data_value=value
        )
        self.logger.debug(f"Packet generated for message: {message}")

        if self._command_queue is None:
            raise RuntimeError("No command queue registered")

        future = Future()
        self._command_queue.put((future, message))
        result = future.result()
        if not result.status:
            self._handle_bad_status(result)

        if future.exception() is not None:
            raise e

        return future.result()

    def _handle_bad_status(self, response: IncomingMessage) -> None:
        try:
            error_code = ModuleErrorCodes[response.data_value]
            self.logger.warning(f"Response failed with error code {error_code}")
            raise FirmwareException(f"Error Code: {error_code}")
        except KeyError:
            raise FirmwareException(
                f"Unknown error code returned - {response.data_value}"
            )
        except Exception as e:
            self.logger.error(f"Unknown error occured when reading response")
            raise e

    def positions_known(self) -> bool:
        return None in list(self._positions_to_steps.values())

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
