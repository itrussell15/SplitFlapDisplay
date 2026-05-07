import enum
import struct
from dataclasses import dataclass


class ModuleCommand(enum.Enum):
    HOME = 0
    GET_POSITION = 1
    MOVE_TO_POSITION = 2
    STOP = 3
    SET_SPEED = 4
    GET_SPEED = 5


@dataclass
class BaseMessage:
    start_value: int
    module_id: int
    command: ModuleCommand
    end_value: int
    data_value: int = 255

    def __post_init__(self) -> None:
        self._struct_string = "<BBBHBB"
        self._data_packet = [
            self.start_value,
            self.module_id,
            self.command.value,
            self.data_value,
            self._create_checksum(),
            self.end_value
        ]

    def _create_checksum(self) -> bytes:
        low_byte = self.data_value & 0xFF
        high_byte = (self.data_value >> 8) & 0xFF
        return self.module_id ^ self.command.value ^ low_byte ^ high_byte

    def generate_packet(self) -> bytes:
        checksum = self._create_checksum()
        return struct.pack(self._struct_string, *self._data_packet) 


@dataclass(kw_only=True)
class OutgoingMessage(BaseMessage):
    start_value: int = 2
    end_value: int = 3


@dataclass(kw_only=True)
class IncomingMessage(BaseMessage):
    status: bool
    start_value: int = 4
    end_value: int = 5

    def __post_init__(self) -> None:
        super().__post_init__()
        self._struct_string = '<BBB?HBB'

    def _create_checksum(self) -> bytes:
        tmp = super()._create_checksum()
        return tmp ^ self.status
    
    def generate_packet(self) -> bytes:
        checksum = self.module_id ^ self.command.value ^ low_byte ^ high_byte
        return struct.pack(self._struct_string, self.start_value, self.module_id, self.command.value, self.status, self.data_value, checksum, self.end_value) 

