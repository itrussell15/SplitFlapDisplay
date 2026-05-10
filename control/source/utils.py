import logging
import serial
import time
from typing import Optional

class SerialControl:
    def __init__(self, port: str, baudrate: int=9600, timeout: int=1):
        self.logger = logging.getLogger(f"{self.__class__.__name__}({port}")
        self.port = port
        self.baudrate = baudrate
        self._timeout = timeout
        self.timeout = timeout
        self.connection = None
        self.buffer = []

    @property
    def timeout(self) -> float:
        return self._timeout

    @timeout.setter
    def timeout(self, value: float) -> None:
        if value < 0:
            raise ValueError("Value must be non-negative")
        self._timeout = value

    def connect(self):
        """Attempts to open the serial port."""
        try:
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            self.logger.debug(f"✅ Connected to {self.port}")
        except serial.SerialException as e:
            self.logger.debug(f"❌ Error connecting to {self.port}: {e}")

    def send(self, message: bytes):
        """Encodes and sends a string to the bus."""
        if self.connection and self.connection.is_open:
            # Adding a newline is common practice for serial commands
            self.connection.write(message)
            self.logger.debug(f"TX -> {message}")
        else:
            self.logger.debug("⚠️ Not connected. Cannot send.")

    def read(self, size: int = 1) -> Optional[bytes]:
        """Reads a line from the bus and decodes it."""
        if self.connection and self.connection.is_open:
            line = self.connection.read(size)
            if line:
                self.logger.debug(f"RX <- {line}")
                return line
        return None
    
    # def read_packet(self, start_value: bytes, end_value: bytes, size: int) -> Optional[bytes]:
    #     start_time = time.time()
    #     current_time = 0
    #     while current_time < self.timeout:
    #         self.logger.info(f"Checking for packet... {self.connection.in_waiting >= size}")
    #         if self.connection.in_waiting >= size:
    #                 response = self.connection.read(size)
    #                 return response
    #         time.sleep(0.01)
    #         current_time = time.time() - start_time
    #         self.logger.info(f"Waiting for response... - {current_time}")
    #     self.logger.warning(f"Timeout: No response received within {self.timeout}s")
    #     raise TimeoutError(f"Device on {self.port} failed to respond within {self.timeout}s")

    def read_packet(self, start_value: byte, end_value: byte, size: int) -> Optional[bytes]:
        buffer = bytes()
        data = end_value
        start_time = time.time()
        timed_out = False
        while not timed_out:
            if self.connection.in_waiting >= size:
                data = self.connection.read()
                self.logger.info(f"Data: {data}")
                if data == start_value:
                    break
            time_delta = time.time() - start_time
            timed_out = time_delta > self.timeout
        
        if timed_out:
            raise TimeoutError(f"Device on {self.port} failed to respond within {self.timeout}s")

        buffer += data
        for _ in range(size-2):
            buffer += self.connection.read()

        data = self.connection.read()
        if data != end_value:
            self.logger.warning(f"Malformed Packet: {buffer}")
            return None
        else:
            buffer += data
        
        self.logger.debug(f"Packet received: {buffer}")
        return buffer

    def close(self):
        """Closes the connection cleanly."""
        if self.connection:
            self.connection.close()
            self.logger.debug("🔌 Connection closed.")

    @property
    def is_data_waiting(self) -> bool:
        if not self.connection:
            raise ConnectionError(f"{self.port} not connected")
        return self.connection.in_waiting > 0

# Functions
def create_logger(level = logging.DEBUG, spacing: int = 15):
    logging.basicConfig(
        level=level,
        format=f'[%(levelname)-8s][%(name)-{spacing}s] %(message)s',
        datefmt='%H:%M:%S'
    )


