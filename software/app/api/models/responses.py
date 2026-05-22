from typing import List
from pydantic import BaseModel
from .common import Location


class MessageTimes(BaseModel):
    send: float
    receive: float
    total: float

class ModuleResponse(BaseModel):
    # We omit start_value and end_value here
    location: Location
    command: int
    data_value: int
    status: bool
    latency_ms: MessageTimes

class DisplayResponse(BaseModel):
    request_time: str
    data: List[ModuleResponse]

class DiscoverResponse(BaseModel):
    request_time: str
    num_modules: int
    num_buses: int
    locations: List[Location]