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

    def to_dict(self) -> Dict[str, int]:
        return {"minutes": self.minutes, "seconds": self.seconds}


class AddItemRequest(BaseModel):
    item_type: str
    parameters: Dict[str, Any]


class AddEntryRequest(BaseModel):
    item_type: str
    parameters: Dict[str, Any]
    duration: FrequencyModel


class ItemResponse(BaseModel):
    name: str
    frequency: Optional[FrequencyModel]
    params: Dict[str, Any]


class EntryResponse(BaseModel):
    index: int
    item: ItemResponse
    duration: Optional[FrequencyModel]
    uuid: str


class TimeData(BaseModel):
    start: Optional[float] = None
    end: Optional[float] = None
    remaining: Optional[float] = None
    elapsed: Optional[float] = None


class ActiveEntryResponse(BaseModel):
    entry: EntryResponse
    time_data: Optional[TimeData] = None


class PlaylistResponse(BaseModel):
    current_index: Optional[int] = None
    current_entry: Optional[EntryResponse] = None
    is_active: bool
    entries: List[EntryResponse]


class StatusResponse(BaseModel):
    is_active: bool
    numItems: int
    currentEntry: Optional[EntryResponse] = None
    currentEntryTime: Optional[TimeData] = None
