from __future__ import annotations

import enum
import inspect
import json
import logging
import os
import sys
from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.components.core.playlist import PlaylistItem
from app.components.core.trigger import Trigger
from control.source.display_controller import DisplayInfo
from control.source.flaps import Flap


class DisplayItemType(enum.Enum):
    STATIC = 0
    APP = 1


@dataclass
class DisplayItemUpdate:
    flaps: Union[Dict[Tuple[int, int], str], Dict[Tuple[int, int], int]]
    needs_resolving: bool = True


class DisplayItem(PlaylistItem):

    description: Optional[str] = None
    app_image: Optional[str] = None

    def __init__(
        self,
        name: str,
        item_type: DisplayItemType,
        params: Dict[str, Any],
        trigger_factory: Optional[Callable[[Callable[[], None]], Trigger]] = None,
    ) -> None:
        super().__init__(name, trigger_factory=trigger_factory)
        self._display_info = None
        self._display_function = None
        self._resolve_function = None
        self._display_data = {}
        self.params = self._filter_params(params)

    @classmethod
    @abstractmethod
    def trigger_factory(cls, callback: Callable[[], None]) -> Trigger: ...

    def __repr__(self) -> str:
        return f"DisplayPlaylistItem({self._name})"

    @abstractmethod
    def update(self, display_info: DisplayInfo) -> Optional[DisplayItemUpdate]:
        pass

    def activate(self, update_on_start: bool = True) -> None:
        self._check_missing_display_info()
        if self._display_function is None:
            raise RuntimeError(
                "No display function set. Set it with `add_display_function`"
            )
        if self._resolve_function is None:
            raise RuntimeError(
                "No display function set. Set it with `add_resolve_function`"
            )
        super().activate(update_on_start)

    def add_display_info(self, display_info: DisplayInfo) -> None:
        self.logger.debug("Added display info")
        self._display_info = display_info

    def add_resolve_function(
        self, function: Callable[Dict[Tuple[int, int], str], Dict[Tuple[int, int]]]
    ):
        self.logger.debug(f"Added resolve function -> {function.__name__}")
        self._resolve_function = function

    def add_display_function(
        self, function: Callable[Dict[Tuple[int, int], int], None]
    ) -> None:
        self.logger.debug(f"Added display function -> {function.__name__}")
        self._display_function = function

    def default_display(self) -> Dict[Tuple[int, int], int]:
        self._check_missing_display_info()
        output = {}
        for row in range(self._display_info.rows):
            for column in range(self._display_info.columns):
                output[(row, column)] = self.default_flap

    def _execute_update(self) -> None:
        """Generate, resolve and render content for the current activation.

        Stale results and overlapping updates are skipped. Once rendering
        begins, deactivation waits for that render to finish.
        """
        with self._lifecycle_lock:
            if not self._is_active or self._is_updating:
                return
            self._is_updating = True
            generation = self._generation
            display_info = self._display_info
        try:
            request = self.update(display_info)
            if request is None:
                self.logger.debug("Update produced no output - skipping")
                return
            flaps = request.flaps
            if request.needs_resolving:
                self.logger.debug("Update requires resolving")
                flaps = self._resolve_function(flaps)
            with self._lifecycle_lock:
                if not self._is_active or generation != self._generation:
                    return
                self._display_function(flaps)
        finally:
            with self._lifecycle_lock:
                self._is_updating = False

    def _filter_params(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        output = {}
        for key, value in parameters.items():
            if key.startswith("__") or key.startswith("_"):
                continue
            if key in ["self", "frequency", "trigger_factory"]:
                continue
            output[key] = value
        return output

    def _check_missing_display_info(self) -> None:
        if self._display_info is None:
            raise RuntimeError("No display info set. Set it with `add_display_info`")
