import logging
import serial
import time
import threading
from queue import Queue
from typing import Optional
from abc import ABC, abstractmethod


class SerialControl:
    def __init__(self, port: str, baudrate: int=9600, timeout: int=1):
        self.logger = logging.getLogger(f"{self.__class__.__name__}({port}")
        self.port = port
        self.baudrate = baudrate
        self._timeout = timeout
        self.timeout = timeout
        self.connection = None
        self.bad_packets = []

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
    
    def read_packet(self, start_value: byte, end_value: byte, size: int) -> Optional[bytes]:
        buffer = bytes()
        data = end_value
        start_time = time.time()
        timed_out = False
        while not timed_out:
            if self.connection.in_waiting >= size:
                data = self.connection.read()
                self.logger.debug(f"Data: {data}")
                if data == start_value:
                    break
            time_delta = time.time() - start_time
            timed_out = time_delta > self.timeout
        
        if timed_out:
            raise TimeoutError(f"Device on {self.port} failed to respond within {self.timeout}s")

        buffer += data
        for _ in range(size-2):
            byte_read = self.connection.read()
            self.logger.debug(f"Read byte: {byte_read}")
            buffer += byte_read

        data = self.connection.read()
        self.logger.debug(f"Read end byte: {data} (looking for {end_value})")
        if data != end_value:
            self.logger.warning(f"Malformed Packet: {buffer} + {data}")
            self.bad_packets.append(buffer + data)
            return buffer + data
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


class SerialProcessor(ABC, SerialControl): 

    def __init__(self, port: str, baudrate: int=9600, timeout: int=1, max_queue_size: int = 64) -> None:
        SerialControl.__init__(self, port, baudrate, timeout)
        self.queue = Queue(maxsize=max_queue_size)
        self.processor = self.create_queue_processor()

    def worker(self):
        while True:
            try:
                start_time = time.time()
                item = self.queue.get()
                self.logger.info(f"Processing: {item}")
                self._send_serial_command(item.encode())
                response = self._read_serial_response()
                self.logger.info(f"Response: {response}")
                self._handle_response(response, item)
                self.queue.task_done()
                self.logger.info(f"Processing Time: {time.time() - start_time}")
            except Exception as e:
                self.logger.error(str(e))

    def create_queue_processor(self) -> threading.Thread:
        return threading.Thread(target=self.worker, daemon=True)

    def _send_serial_command(self, command: bytes) -> bool:
        self.logger.debug(f"Raw packet being sent {command}")
        self.send(command)

    @abstractmethod
    def _read_serial_response(self) -> BaseMessage:
        pass

    @abstractmethod
    def _handle_response(self, incoming: BaseMessage, outgoing: BaseMessage) -> None:
        pass

    def close(self) -> None:
        if not self.queue.empty():
            self.logger.info(f"Waiting for {self.queue.qsize()} commands to complete before closing")
        while not self.queue.empty():
            time.sleep(0.1)
        self.logger.info("Closing serial connection")
        super().close()