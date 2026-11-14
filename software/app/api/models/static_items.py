from pydantic import BaseModel
from app.api.models.common import Location
from app.components.display_playlist.base_apps.static import StaticDisplayItem
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

    def to_static_display_item(self) -> StaticDisplayItem:
        output = {}
        for item in self.data:
            output[(item.location.as_tuple())] = item.position
        return StaticDisplayItem(name=self.name, flaps=output, needs_resolving=False)


class StaticItems(BaseModel):
    num_items: int
    items: Dict[str, StaticItems]
