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
    file_location: str  


class StaticItems(BaseModel):
    request_time: str
    items: Dict[str, StaticItemResponse]
    
