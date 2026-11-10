from pydantic import BaseModel
from app.api.models.common import Location
from .requests import DisplayPositionRequest

from typing import Dict, List


class StaticItemRequest(DisplayPositionRequest):
    name: str


class StaticModuleData(BaseModel):
    location: Location
    position: int


class StaticItemResponse(BaseModel):
    name: str
    data: List[StaticModuleData]


class AddStaticItemResponse(StaticItemResponse):
    creation_time: str


class StaticItem(BaseModel):
    name: str
    uuid: str
    request_time: str
    data: List[StaticModuleData]
    

class StaticItems(BaseModel):
    num_items: int
    items: Dict[str, StaticItems]
