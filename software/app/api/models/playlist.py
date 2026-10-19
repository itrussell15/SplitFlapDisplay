from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.components.display_playlist.display_item import DisplayItem


class FrequencyResponse(BaseModel):
    minutes: int
    seconds: int


class AddItemRequest(BaseModel):
    item_type: str
    parameters: Dict[str, Any]


class ItemResponse(BaseModel):
    name: str
    uuid: str
    index: int
    frequency: FrequencyResponse
    params: Dict[str, Any]


class TimeData(BaseModel):
    start: Optional[float]
    end: Optional[float]
    remaining: Optional[float]
    elapsed: Optional[float]


class ActiveItemResponse(BaseModel):
    item: ItemResponse
    time_data: TimeData


class PlaylistResponse(BaseModel):
    current_index: int
    is_active: bool
    frequency: FrequencyResponse
    items: List[ItemResponse]


class StatusResponse(BaseModel):
    is_active: bool
    numItems: int
    currentItem: Optional[ItemResponse]
    currentItemTime: Optional[TimeData]