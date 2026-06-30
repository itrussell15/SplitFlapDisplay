from typing import List

from pydantic import BaseModel, Field

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


class DiscoverRequest(BaseModel):
    # Search every (row, column) from 1 up to and including these maximums.
    max_row: int = Field(ge=1, le=255)
    max_column: int = Field(ge=1, le=255)


class CalibrationModeRequest(LocationRequest):
    enabled: bool


class HomeOffsetRequest(LocationRequest):
    value: int
