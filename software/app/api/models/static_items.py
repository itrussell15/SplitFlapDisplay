from pydantic import BaseModel
from .requests import DisplayFlapRequest, Location
from .responses import ModuleResponse

from typing import Dict, List



class StaticItemRequest(DisplayFlapRequest):
    name: str


class StaticModuleData(BaseModel):
    location: Location
    value: str


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
