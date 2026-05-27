from typing import List
from pydantic import BaseModel
from .common import Location


class LocationRequest(BaseModel):
    location: Location

class FlapRequest(LocationRequest):
    flap: str

class DisplayFlapRequest(BaseModel):
    request_time: str
    module_requests: List[FlapRequest]

class PositionRequest(LocationRequest):
    position: int

class DisplayPositionRequest(BaseModel):
    request_time: str
    module_requests: List[PositionRequest]

class StepRequest(LocationRequest):
    step: int