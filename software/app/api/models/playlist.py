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
    

class PlaylistResponse(BaseModel):
    current_index: int
    is_active: bool
    frequency: FrequencyResponse
    items: List[ItemResponse]