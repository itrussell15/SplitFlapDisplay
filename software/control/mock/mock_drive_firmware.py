import sys
import time 
import logging
import queue
import threading
import serial 
import struct
from pathlib import Path
from concurrent.futures import Future
from dataclasses import dataclass

from typing import List, Tuple

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
print(sys.path)

from control.source.dataclasses_ import IncomingMessage, OutgoingMessage
from control.source.module_controller import (
    ModuleCommand,
    ModuleController,
    EepromLocations,
    MOTOR_RESOLUTION,
    NUM_POSITIONS
)
from control.source.serial_processor import SerialProcessor, SerialControl
from utils import create_logger

EXAMPLE_INCOMING_MESSAGE = IncomingMessage(
    row=0, column=0, sequence_id=0, command=ModuleCommand.HOME, status=True
)
EXAMPLE_OUTGOING_MESSAGE = OutgoingMessage(row=0, column=0, command=ModuleCommand.HOME)

FIRWARE_VERSION_MAJOR = 255
FIRWARE_VERSION_MINOR = 255
HOME_OFFSET_VALUE = 2500
AUTO_HOME = True
HALL_RANGE = [2500, 2550]

class MockModule(ModuleController):

    def __init__(self, row: int, column: int) -> None:
        self.logger = logging.getLogger(f"MockModule({row}, {column})")
        self._step = 0
        self.calibration_mode = False
        self.max_steps = MOTOR_RESOLUTION

        # Generate position values
        self.positions = {i: i * (MOTOR_RESOLUTION // NUM_POSITIONS) for i in range(NUM_POSITIONS)}
        self.home_offset = HOME_OFFSET_VALUE

        self.eeprom = {
            EepromLocations.MODULE_ROW_LOCATION.value: row,
            EepromLocations.MODULE_COLUMN_LOCATION.value: column,
            EepromLocations.MAJOR_FIRMWARE_LOCATION.value: FIRWARE_VERSION_MAJOR,
            EepromLocations.MINOR_FIRMWARE_LOCATION.value: FIRWARE_VERSION_MINOR,
            EepromLocations.AUTO_HOME_LOCATION.value: AUTO_HOME,
            EepromLocations.HOME_OFFSET_VALUE_LOCATION.value: HOME_OFFSET_VALUE,
            EepromLocations.HOME_OFFSET_VALUE_LOCATION.value: HOME_OFFSET_VALUE,
            EepromLocations.MAX_STEP_LOCATION.value: MOTOR_RESOLUTION // 256,
            EepromLocations.MAX_STEP_LOCATION.value + 1: MOTOR_RESOLUTION % 256,
            EepromLocations.POSITION_VALUES_START_LOCATION.value: 100
        }

    @property
    def steps(self) -> None:
        return self._step

    @steps.setter
    def steps(self, value: int) -> None:
        if value < 0 or value >= MOTOR_RESOLUTION:
            raise ValueError(f"Step values must be between 0-{MOTOR_RESOLUTION}")
        self._step = value

    @property
    def hall_active(self) -> bool:
        return self.step >= HALL_RANGE[0] and self.step <= HALL_RANGE[1]


class MockFirmware(SerialProcessor):

    def __init__(self, port: str, module_ids: List[Tuple[int, int]]) -> None:
        super().__init__(port)
        self.connect()
        self.module_ids = module_ids
        self.stop_event = threading.Event()
        self.commands_processed: int = 0

        self.logger.info(f"Creating mock modules for {module_ids}")
        self._modules = {}
        for module_id in module_ids:
            module = MockModule(*module_id)
            module.register_command_queue(self.queue, port)
            self._modules[module_id] = module

    def worker(self):
        """Process incoming serial commands and return module responses.

        Unlike the old loop, this writes the generated response directly to the
        serial connection and keeps running after a decode / processing error.
        """
        self.logger.debug("Mock firmware worker started")
        packet_size = struct.calcsize(OutgoingMessage._struct_string)

        while not self._stop_event.is_set():
            try:
                if not self.connection or not self.connection.is_open:
                    time.sleep(0.01)
                    continue

                if not self.is_data_waiting:
                    time.sleep(0.01)
                    continue

                raw = self.connection.read(self.connection.in_waiting)
                if not raw:
                    continue

                for offset in range(0, len(raw), packet_size):
                    chunk = raw[offset : offset + packet_size]
                    if len(chunk) < packet_size:
                        self.logger.warning(
                            "Discarding partial packet from mock firmware: %s", chunk
                        )
                        continue

                    try:
                        message = OutgoingMessage.decode(chunk)
                    except Exception as exc:
                        self.logger.warning(
                            "Unable to decode mock-firmware command %r: %s",
                            chunk,
                            exc,
                        )
                        continue

                    self.logger.info(f"Incoming message: {message}")
                    response = self._query_modules(message)
                    self.logger.info(f"Response: {response}")
                    if response is not None:
                        self.send(response.encode())

                if self.connection and self.connection.is_open:
                    self.connection.reset_input_buffer()

            except serial.SerialException as exc:
                self.logger.exception("Mock serial failure: %s", exc)
                if self.connection and self.connection.is_open:
                    self.connection.reset_input_buffer()
            except Exception as exc:
                self.logger.exception("Unexpected mock worker failure: %s", exc)
                if self.connection and self.connection.is_open:
                    self.connection.reset_input_buffer()

            time.sleep(0.01)

    def listen(self):
        """Backward-compatible entry point for the mock firmware."""
        self.worker()

    def advance_queue(self, sequence_id: int) -> None:
        if self.connection and self.connection.is_open:
            self.connection.reset_input_buffer()
        item = self.queue.get()
        try:
            self._send_serial_command(item)
        finally:
            self.queue.task_done()

    def _read_serial_response(self) -> IncomingMessage:
        incoming_packet = self.read_packet(
            start_value=struct.pack("B", EXAMPLE_OUTGOING_MESSAGE.start_value),
            end_value=struct.pack("B", EXAMPLE_OUTGOING_MESSAGE.end_value),
            size=EXAMPLE_OUTGOING_MESSAGE.packet_size,
        )
        if not incoming_packet:
            self.logger.warning("No response")
            return None
        return incoming_packet

    def _handle_response(
        self, incoming: OutgoingMessage, outgoing: IncomingMessage, sequence_id: int
    ) -> OutgoingMessage:
        """
        Since we are mimicking the module firmware, the incoming message is an Outgoing message from the software side.
        """

        if not incoming:
            self.logger.warning(f"No response to {outgoing}")
            return

        try:
            response = OutgoingMessage.decode(incoming)
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

    def _query_modules(self, message: OutgoingMessage) -> IncomingMessage:
        response = IncomingMessage(
            row=message.row,
            column=message.column,
            command=message.command,
            sequence_id=message.sequence_id,
            status=True
        )
        location = (message.row, message.column)
        if location not in self._modules:
            return

        target_module = self._modules[(message.row, message.column)]
        # TODO Make this async so that it closer resembles the actual modules
        match message.command:
            case ModuleCommand.PING:
                response.data_value = 0
            case ModuleCommand.HOME:
                response.data_value = 0
            case ModuleCommand.GET_STEPS:
                response.data_value = target_module.steps
            case ModuleCommand.MOVE_TO_STEP:
                target_module.steps = message.data_value
                response.data_value = target_module.steps
            case ModuleCommand.SET_POSITION:
                target_module.positions[message.data_value] = target_module.steps
                response.data_value = target_module.steps
            case ModuleCommand.MOVE_TO_POSITION:
                step = target_module.positions[message.data_value]
                target_module.steps = step
                response.data_value = step
            case ModuleCommand.GET_POSITION:
                response.data_value = target_module.positions[int(message.data_value)]
            case ModuleCommand.MOVE_STEPS:
                target_module.steps = (target_module.steps + message.data_value) % MOTOR_RESOLUTION
                response.data_value = target_module.steps
            case ModuleCommand.GET_HALL_EFFECT_STATUS:
                response.data_value = int(target_module.hall_active)
            case ModuleCommand.IS_MOVING:
                response.data_value = False
            case ModuleCommand.MOTOR_NUM_STEPS:
                response.data_value = MOTOR_RESOLUTION
            case ModuleCommand.SET_HOME_OFFSET:
                target_module.home_offset = message.data_value
            case ModuleCommand.GET_HOME_OFFSET:
                message.data_value = target_module.home_offset
            case ModuleCommand.SET_AUTO_HOME:
                target_module.auto_home = message.data_value
            case ModuleCommand.SET_MAX_STEPS:
                eeprom_location = EepromLocations.MAX_STEP_LOCATION
                response.data_value = target_module.eeprom[eeprom_location]
            case ModuleCommand.GET_EEPROM_VALUE:
                response.data_value = target_module.eeprom[message.data_value]
            case ModuleCommand.SET_CALIBRATION_MODE:
                mode = bool(message.data_value)
                target_module.calibration_mode = mode
                message.data_value = mode
            case _:
                return None

        return response

if __name__ == "__main__":

    create_logger()

    all_modules = []
    for row in range(1, 4):
        for column in range(1, 16):
            all_modules.append((row, column))
    
    Firmware = MockFirmware("/tmp/vcom_firmware", all_modules)
    Firmware.start_processor()
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        Firmware.close()
