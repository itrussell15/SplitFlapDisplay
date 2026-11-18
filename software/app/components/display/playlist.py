from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.components.core.app_loader import AppLoader
from app.components.core.playlist import Playlist, PlaylistEntry
from app.components.core.updater import UpdateFrequency
from app.components.display.display_item import DisplayItem
from control.source.display_controller import DisplayInfo

BASE_APP_PATH = str(Path(__file__).parent / "base_apps")


class DisplayPlaylist(Playlist):
    """Configure display items while Playlist owns playback and entry timing.

    Entries may be supplied before display setup. The configuration setters
    apply to all existing entries, and later additions receive the same setup.
    Supply display information, a resolver, and an output function before
    starting playback. Configuration and entry changes require a stopped playlist.
    """

    def __init__(
        self,
        entries: Optional[List[PlaylistEntry]] = None,
        app_folders: Optional[List[str]] = None,
    ) -> None:
        super().__init__()
        self._display_info: Optional[DisplayInfo] = None
        self._resolve_function = None
        self._display_function = None
        self._apps = AppLoader(
            desired_class=DisplayItem,
            sources=app_folders if app_folders is not None else [BASE_APP_PATH],
        )
        if entries is not None:
            for entry in entries:
                if not isinstance(entry, PlaylistEntry):
                    raise TypeError("entries must contain PlaylistEntry objects")
                self.add_entry(entry)

    def add_display_info(self, display_info: DisplayInfo) -> None:
        with self._lock:
            if self._is_active:
                raise RuntimeError("Stop the playlist before changing display info")
            self._display_info = display_info
            for item in self.items:
                item.add_display_info(display_info)

    def add_resolve_function(
        self,
        function: Callable[[Dict[Tuple[int, int], str]], Dict[Tuple[int, int], int]],
    ) -> None:
        with self._lock:
            if self._is_active:
                raise RuntimeError("Stop the playlist before changing the resolver")
            self._resolve_function = function
            for item in self.items:
                item.add_resolve_function(function)

    def add_display_function(
        self, function: Callable[[Dict[Tuple[int, int], int]], None]
    ) -> None:
        with self._lock:
            if self._is_active:
                raise RuntimeError(
                    "Stop the playlist before changing the display function"
                )
            self._display_function = function
            for item in self.items:
                item.add_display_function(function)

    def add_entry(
        self,
        item: Union[DisplayItem, PlaylistEntry],
        duration: Optional[UpdateFrequency] = None,
    ) -> PlaylistEntry:
        with self._lock:
            if self._is_active:
                raise RuntimeError("Stop the playlist before adding entries")
            if isinstance(item, PlaylistEntry):
                if duration is not None:
                    raise TypeError("duration is already part of the PlaylistEntry")
                entry = item
            else:
                entry = PlaylistEntry(item=item, duration=duration)
            if not isinstance(entry.item, DisplayItem):
                raise TypeError(
                    "DisplayPlaylist entries must contain DisplayItem objects"
                )
            if self._display_info is not None:
                entry.item.add_display_info(self._display_info)
            if self._resolve_function is not None:
                entry.item.add_resolve_function(self._resolve_function)
            if self._display_function is not None:
                entry.item.add_display_function(self._display_function)
            return super().add_entry(entry)

    @property
    def apps(self) -> AppLoader:
        return self._apps

    @property
    def available_apps(self) -> List[str]:
        return self._apps.list()
