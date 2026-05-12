from __future__ import annotations

import enum 
import struct
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass


class ModuleCommand(enum.Enum):
    PING = 0
    HOME = 1
    STOP = 2
    GET_POSITION = 3
    SET_POSITION = 4 # Stores position in EEPROM
    MOVE_TO_POSITION = 5
    GET_SPEED = 6
    SET_SPEED = 7
    GET_STEPS = 8
    MOVE_TO_STEP = 9


@dataclass
class BaseMessage(ABC):
    start_value: int
    module_id: int
    command: ModuleCommand
    end_value: int
    data_value: int = 255
    _struct_string = "<BBBHBB"

    def __post_init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._data_packet = [
            self.start_value,
            self.module_id,
            self.command.value,
            self.data_value,
            self._create_checksum(),
            self.end_value
        ]

    @staticmethod
    def checksum(data_value: int, command_value: int, module_id: int) -> int:
        low_byte = data_value & 0xFF
        high_byte = (data_value >> 8) & 0xFF
        return module_id ^ command_value ^ low_byte ^ high_byte

    def _create_checksum(self) -> int:
        return self.checksum(self.data_value, self.command.value, self.module_id)

    def encode(self) -> bytes:
        return struct.pack(self._struct_string, *self._data_packet) 

    @classmethod
    def decode(cls, message: bytes) -> BaseMessage:
        try:
            output = struct.unpack(cls._struct_string, message)
            return cls._parse_output(output)
        except Exception as e:
            raise e

    @classmethod
    @abstractmethod
    def _parse_output(cls, data: bytes) -> OutgoingMessage:
        pass

    @property
    def packet_size(cls) -> int:
        return struct.calcsize(cls._struct_string)


@dataclass(kw_only=True)
class OutgoingMessage(BaseMessage):
    start_value: int = 2
    end_value: int = 3

    def __post_init__(self) -> None:
        super().__post_init__()
        assert self.start_value == 2
        assert self.end_value == 3

    @classmethod
    def _parse_output(cls, data: bytes) -> OutgoingMessage:
        module_id = data[1]
        command_value = data[2]
        data_value = data[3]

        assert data[4] == cls._checksum(data_value, command_value, module_id)
        return cls(
            module_id=module_id,
            command=ModuleCommand(command_value),
            data_value=data_value,
        )

@dataclass(kw_only=True)
class IncomingMessage(BaseMessage):
    status: bool
    start_value: int = 4
    end_value: int = 5
    _struct_string = '<BBBH?BB'

    def __post_init__(self) -> None:
        super().__post_init__()
        self._data_packet = [
            self.start_value,
            self.module_id,
            self.command.value,
            self.data_value,
            self.status,
            self._create_checksum(),
            self.end_value
        ]
    
    def encode(self) -> bytes:
        checksum = self._create_checksum()
        return struct.pack(self._struct_string, self.start_value, self.module_id, self.command.value, self.status, self.data_value, checksum, self.end_value) 

    @classmethod
    def _parse_output(cls, data: bytes) -> OutgoingMessage:
        module_id = data[1]
        command_value = data[2]
        data_value = data[3]
        status = data[4]

        calculated_checksum = cls.checksum(data_value, command_value, module_id, status)
        if data[5] != calculated_checksum:
            raise ValueError(f"Received Checksum doesn't match calculated value. {data[5]} != {calculated_checksum}")
        return cls(
            module_id=module_id,
            command=ModuleCommand(command_value),
            data_value=data_value,
            status=status
        )

    @staticmethod
    def checksum(data_value: int, command_value: int, module_id: int, status: bool) -> int:
        low_byte = data_value & 0xFF
        high_byte = (data_value >> 8) & 0xFF
        return module_id ^ command_value ^ low_byte ^ high_byte ^ status
    
    def _create_checksum(self) -> bytes:
        return self.checksum(self.data_value, self.command.value, self.module_id, self.status)