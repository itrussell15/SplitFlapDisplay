from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.components.core.updater import UpdateFrequency
from app.components.display.display_item import DisplayItem
from pydantic import BaseModel


class FrequencyModel(BaseModel):
    minutes: int
    seconds: int

    def to_update_frequency(self) -> UpdateFrequency:
        return UpdateFrequency(minutes=self.minutes, seconds=self.seconds)


class AddItemRequest(BaseModel):
    item_type: str
    parameters: Dict[str, Any]


class AddEntryRequest(BaseModel):
    item_type: str
    duration: Optional[FrequencyModel]
    parameters: Dict[str, Any]


class ItemResponse(BaseModel):
    name: str
    uuid: str
    index: int
    frequency: Optional[FrequencyModel]
    params: Dict[str, Any]


class EntryResponse(BaseModel):
    item: ItemResponse
    frequency: Optional[FrequencyModel]


class TimeData(BaseModel):
    start: Optional[float]
    end: Optional[float]
    remaining: Optional[float]
    elapsed: Optional[float]


class ActiveEntryResponse(BaseModel):
    entry: EntryResponse
    time_data: Optional[TimeData]


class PlaylistResponse(BaseModel):
    current_index: int
    is_active: bool
    frequency: FrequencyModel
    entries: List[EntryResponse]


class StatusResponse(BaseModel):
    is_active: bool
    numItems: int
    playlistFrequency: FrequencyModel
    currentItem: Optional[ItemResponse]
    playlistTime: Optional[TimeData]
    currentItemTime: Optional[TimeData]
