import os
import sys
import enum
from munch import munchify
import json
from dataclasses import dataclass
from abc import abstractmethod
import logging
from pathlib import Path

from typing import Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
print(sys.path)

from app.components.core.playlist import PlaylistItem
from app.components.core.updater import UpdateFrequency
from control.source.flaps import Flap
from control.source.display_controller import DisplayInfo

class DisplayItemType(enum.Enum):
    STATIC = 0
    APP = 1


class DisplayItem(PlaylistItem):

    def __init__(
        self,
        name: str,
        item_type: PlaylistItemType,
        frequency: Optional[UpdateFrequency] = None,
        default_flap: Flap = Flap.BLANK
    ) -> None:
        super().__init__(name, frequency)
        self._display_info = None
        self._display_function = None
        self._default_flap = default_flap

    def __repr__(self) -> str:
        return f"DisplayPlaylistItem({self.name})"

    @abstractmethod
    def update(self, display_info: DisplayInfo) -> Dict[Tuple[int, int], str]:
        pass

    def add_display_info(self, display_info: DisplayInfo) -> None:
        self.logger.debug("Added display info")
        self._display_info = display_info
    
    def add_display_function(self, function: Callable[Dict[Tuple[int, int], Flap], Any]) -> None:
        self.logger.debug(f"Added display function -> {function.__name__}")
        self._display_function = function

    def _request_to_flaps(self, request: Dict[Tuple[int, int], Union[str, int]]) -> Dict[Tuple[int, int], Flap]:
        flaps = {}
        for location in self._display_info.module_locations:
            if location in request:
                value = Flap[request[location]]
            else:
                value = self._default_flap
            flaps.update({location: value})
        return flaps    

    def _top_level_update(self) -> None:
        self._is_updating = True
        request = self.update(self._display_info)
        if request is not None:
            flaps = self._request_to_flaps(request)
            self._display_function(flaps)
        else:
            self.logger.debug(f"Update invoked, but not change in output - skipping")
        self._is_updating = False

class StaticDisplayItem(DisplayItem):

    def __init__(
        self,
        name: str, 
        flaps: Dict[Tuple[int, int], str]
    ) -> None:
        super().__init__(name, item_type=DisplayItemType.STATIC)
        self.flaps = flaps

    @classmethod
    def from_dict(self, data: Dict[str, Any]) -> StaticDisplayItem:
        items = {}
        for module in data.modules:
            items[(module.location.row, module.location.column)] = module.flap
        return StaticDisplayItem(
            name=data.name,
            flaps=items
        )

    @classmethod
    def from_json(self, path: str) -> StaticDisplayItem:
        if not os.path.exists(path):
            FileNotFoundError(f"{path} does not exist")
        
        if os.path.splitext(path)[-1] != ".json":
            this_type = os.path.splitext(path)[-1]
            raise TypeError(f"Unable to process file type {this_type}")

        with open(path, "r") as file:
            data = munchify(json.load(file))
        
        return cls.from_dict(data)

    def __repr__(self) -> str:
        return f"StaticDisplayItem({self.name})"

    def update(self, display_info: DisplayInfo) -> Dict[Tuple[int, int], str]:
        return self.flaps