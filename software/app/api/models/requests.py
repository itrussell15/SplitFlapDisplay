from typing import List
from pydantic import BaseModel
from .common import Location


class FlapRequest(BaseModel):
    location: Location
    flap: str

class DisplayFlapRequest(BaseModel):
    request_time: str
    module_requests: List[FlapRequest]

class PositionRequest(BaseModel):
    location: Location
    position: int

class DisplayPositionRequest(BaseModel):
    request_time: str
    module_requests: List[PositionRequest]

class StepRequest(BaseModel):
    location: Location
    step: int