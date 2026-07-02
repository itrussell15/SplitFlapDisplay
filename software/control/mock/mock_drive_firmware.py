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

        # Generate position values
        self.positions = {i: i * (MOTOR_RESOLUTION // NUM_POSITIONS) for i in range(NUM_POSITIONS)}
        self.home_offset = HOME_OFFSET_VALUE

        self.eeprom = {
            EepromLocations.MODULE_ROW_LOCATION: row,
            EepromLocations.MODULE_COLUMN_LOCATION: column,
            EepromLocations.MAJOR_FIRMWARE_LOCATION: FIRWARE_VERSION_MAJOR,
            EepromLocations.MINOR_FIRMWARE_LOCATION: FIRWARE_VERSION_MINOR,
            EepromLocations.AUTO_HOME_LOCATION: AUTO_HOME,
            EepromLocations.HOME_OFFSET_VALUE_LOCATION: HOME_OFFSET_VALUE,
            EepromLocations.MAX_STEP_LOCATION: MOTOR_RESOLUTION,
            EepromLocations.POSITION_VALUES_START_LOCATION: self.positions
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
            module.register_command_queue(self.queue)
            self._modules[module_id] = module

    def listen(self):
        if not self.connection or not self.connection.is_open:
            raise RuntimeError(f"Connection not opened")
        try:
            while True:
                # Check if there is data waiting in the serial buffer
                if self.is_data_waiting:
                    # Read the incoming data
                    data = self.read(self.data_waiting_size)
                    message = OutgoingMessage.decode(data)
                    self.logger.info(f"Incoming message: {message}")
                    response = self._query_modules(message)
                    self.logger.info(f"Response: {response}")
                    if response:
                        self.queue.put(response.encode())
                    
                    # Optional: Send it back out to the device
                    # ser.write(data) 
                    
                time.sleep(0.01) # Small sleep to prevent CPU spiking
                
        except serial.SerialException as e:
            print(f"Error: {e}")
        except KeyboardInterrupt:
            print("Stopping echo loop...")
        finally:
            # if 'ser' in locals() and ser.is_open:
            self.close()

    def advance_queue(self, sequence_id: int) -> None:
        if self.connection and self.connection.is_open:
            self.connection.reset_input_buffer()
        item = self.queue.get()
        try:
            self._send_serial_command(item)
            # self.process_message(sequence_id, item, future)
            # if future.exception() is not None:
            #     raise future.exception()
            # # Handle the message like the firmware would here
            # self._query_modules(future.result())
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
        target_module = self._modules[(message.row, message.column)]
        match message.command:
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
            case _:
                return None

        return response

if __name__ == "__main__":

    create_logger()
    Firmware = MockFirmware("/tmp/vcom_firmware", [(1, 1)])
    Firmware.start_processor()
    Firmware.listen()
    # while Firmware.is_alive:
    #     try:
    #         time.sleep(0.1)
    #     except KeyboardInterrupt:
    #         Firmware.close()
    #     except Exception:
    #         raise e
    # Firmware.close()
