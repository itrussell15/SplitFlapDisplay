from typing import Dict, List
from pydantic import BaseModel

from .common import AverageLatencyResponse, LatencyResponse


class BusLatencyResponse(BaseModel):
    average: AverageLatencyResponse
    current_window: List[LatencyResponse]


class DisplayLatencyResponse(BaseModel):
    display_repaint_estimate: LatencyResponse
    buses: Dict[str, BusLatencyResponse]