from __future__ import annotations

import os
import sys
import enum
import inspect
from munch import munchify
import json
from abc import abstractmethod
import logging
from pathlib import Path

from typing import Any, Callable, Dict, Optional, Tuple, Union

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.components.core.playlist import PlaylistItem
from app.components.core.updater import UpdateFrequency
from control.source.flaps import Flap
from control.source.display_controller import DisplayInfo

class DisplayItemType(enum.Enum):
    STATIC = 0
    APP = 1


class DisplayItem(PlaylistItem):

    description: Optional[str] = None
    app_image: Optional[str] = None

    def __init__(
        self,
        name: str,
        item_type: DisplayItemType,
        params: Dict[str, Any],
        frequency: Optional[UpdateFrequency] = None,
        default_flap: Flap = Flap.BLANK
    ) -> None:
        super().__init__(name, frequency)
        self._display_info = None
        self._display_function = None
        self._default_flap = default_flap
        self._display_data = {}
        self.params = self._filter_params(params)

    def __repr__(self) -> str:
        return f"DisplayPlaylistItem({self._name})"

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

    def _invoke_update(self) -> None:
        self._is_updating = True
        self._time_status = self._update_time_status()
        request = self.update(self._display_info)
        if request is not None:
            flaps = self._request_to_flaps(request)
            self._display_function(flaps)
        else:
            self.logger.debug(f"Update invoked, but not change in output - skipping")
        self._is_updating = False

    def _filter_params(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        output = {}
        for key, value in parameters.items():
            if key.startswith("__") or key.startswith("_"):
                continue
            if key in ["self", "frequency"]:
                continue
            output[key] = value
        return output