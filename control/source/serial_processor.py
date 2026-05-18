import logging
import threading
import time
from abc import ABC, abstractmethod
from queue import Queue
from typing import Optional

import serial

from .dataclasses_ import BaseMessage


class SerialControl:
    def __init__(self, port: str, baudrate: int = 9600, timeout: int = 1):
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
                port=self.port, baudrate=self.baudrate, timeout=self.timeout
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
            raise ConnectionError("⚠️ Not connected. Cannot send.")

    def read(self, size: int = 1) -> Optional[bytes]:
        """Reads a line from the bus and decodes it."""
        if self.connection and self.connection.is_open:
            line = self.connection.read(size)
            if line:
                self.logger.debug(f"RX <- {line}")
                return line
        return None

    def read_packet(
        self, start_value: bytes, end_value: bytes, size: int
    ) -> Optional[bytes]:
        buffer = bytes()
        data = end_value
        start_time = time.time()
        timed_out = False
        while not timed_out:
            if self.connection.in_waiting >= size:
                data = self.connection.read()
                if data == start_value:
                    break
            time_delta = time.time() - start_time
            timed_out = time_delta > self.timeout

        if timed_out:
            raise TimeoutError(
                f"Device on {self.port} failed to respond within {self.timeout}s"
            )

        buffer += data
        for _ in range(size - 2):
            byte_read = self.connection.read()
            buffer += byte_read

        data = self.connection.read()
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
    def is_connected(self):
        return self.connection is not None

    @property
    def is_data_waiting(self) -> bool:
        if not self.connection:
            raise ConnectionError(f"{self.port} not connected")
        return self.connection.in_waiting > 0


class SerialProcessor(ABC, SerialControl):

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: int = 1,
        max_queue_size: int = 64,
        connect_now: bool = True,
        start: bool = True,
        startup_sleep: float = 0.5
    ) -> None:
        SerialControl.__init__(self, port, baudrate, timeout)
        self.queue = Queue(maxsize=max_queue_size)
        self._is_processing: bool = False

        # Arduino resets when serial port opens - wait for bootloader to finish
        time.sleep(startup_sleep)

        self.processor: Optional[threading.Thread] = None
        if connect_now:
            self.connect()
            if start:
                self.processor = self.start_processor()

    def worker(self):
        sequence_id: int = 0
        while not self._stop_event.is_set():
            if sequence_id > 255:
                self.logger.debug(f"Sequence ID overflow! Resetting to 0")
                sequence_id = 0
            sequence_id += 1
            try:
                start_time = time.time()
                item = self.queue.get()
                self.logger.info(
                    f"Queue Size: {self.queue.qsize()} - Sequence ID {sequence_id}: {item}"
                )
                if isinstance(item, BaseMessage):
                    self._send_serial_command(item.encode(sequence_id))
                else:
                    self.logger.info(f"Packet doesn't need encoding: {item}")
                    self._send_serial_command(item)
                send_time = time.time()
                response = self._read_serial_response()
                respond_time = time.time()
                self.logger.info(f"Response: {response}")
                self._handle_response(response, item, sequence_id)
                handling_time = time.time()
                self.queue.task_done()
                self.logger.debug(f"Total: {handling_time - start_time:.4f} Send Time: {send_time - start_time:.4f} - Respond Time: {respond_time - send_time:.4f} - Handle Time: {handling_time - respond_time:.4f}")
            except Exception as e:
                self.logger.error(str(e))
        self.logger.info("Worker shut down")

    def start_processor(self) -> threading.Thread:
        if not self.is_connected:
            raise ConnectionError("Can't start processing queue with a closed connection")
        self._stop_event = threading.Event()
        self._is_processing = True
        worker = threading.Thread(target=self.worker, daemon=True)
        worker.start()
        self.logger.info(f"{self.__class__.__name__} has started processing")
        return worker

    def stop_processor(self):
        self.logger.debug("Stopping processing thread")
        self._stop_event.set()
        self._is_processing = False

    def _send_serial_command(self, command: bytes) -> bool:
        self.logger.debug(f"Raw packet being sent {command}")
        self.send(command)

    @abstractmethod
    def _read_serial_response(self) -> BaseMessage:
        pass

    @abstractmethod
    def _handle_response(
        self, incoming: BaseMessage, outgoing: BaseMessage, sequence_id: int
    ) -> None:
        pass

    def close(self) -> None:
        if not self.queue.empty():
            self.logger.info(
                f"Waiting for {self.queue.qsize()} commands to complete before closing"
            )
        while not self.queue.empty():
            time.sleep(0.1)
        self.stop_processor()
        time.sleep(0.5)
        self.logger.info("Closing serial connection")
        super().close()

    @property
    def is_processing(self) -> bool:
        return self.is_processing
