import sys
import time 
import logging
import serial 
import struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from source.dataclasses_ import IncomingMessage, OutgoingMessage
from source.module_controller import ModuleCommand, ModuleController
from source.utils import SerialControl, create_logger

MODULE_IDS = [1, 2, 3, 10]

if __name__ == "__main__":

    example_message = OutgoingMessage(1, ModuleCommand.HOME)

    # TODO Add "firmware" code here
    create_logger()
    logger = logging.getLogger("MockFirmware")
    connection = SerialControl("/tmp/vcom_host")
    connection.connect()

    while True:
        if (
            connection.is_data_waiting
            and connection.connection.in_waiting >= example_message.packet_size
        ):
            logger.debug(f"Waiting: {connection.connection.in_waiting}")
            try:
                data = connection.read_packet(
                    struct.pack("B", example_message.start_value),
                    struct.pack("B", example_message.end_value),
                    example_message.packet_size
                )
                if data:
                    message = OutgoingMessage.decode(data)
                    logger.info(f"Message received: {message}")
                    if message.module_id not in MODULE_IDS:
                        logger.warning(f"Incoming message for module {message.module_id} - which is not attached")
                        continue
                    response = IncomingMessage(
                        module_id = message.module_id,
                        status=True,
                        command = message.command
                    )
                    logger.debug(f"Response: {response}")
                    connection.send(response.encode())
            except Exception as e:
                logger.error(str(e))