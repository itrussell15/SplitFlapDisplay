from typing import List
from pydantic import BaseModel


class Location(BaseModel):
    row: int
    column: int

class MessageTimes(BaseModel):
    send: float
    receive: float

class ModuleResponse(BaseModel):
    # We omit start_value and end_value here
    location: Location
    command: int
    data_value: int
    status: bool
    times: MessageTimes

class DisplayResponse(BaseModel):
    request_time: str
    data: List[ModuleResponse]