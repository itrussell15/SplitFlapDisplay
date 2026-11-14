import os
import sys
import json
from munch import munchify
from pathlib import Path
from typing import Any, Callable, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from app.components.core.updater import UpdateFrequency
from app.components.core.playlist import Playlist, PlaylistItem, PlaylistEmptyError
from app.components.core.app_loader import AppLoader
from app.components.display_playlist.display_item import DisplayItem, DisplayItemType
from app.components.display_playlist.base_apps.static import StaticDisplayItem

BASE_APP_PATH = os.path.join(os.path.dirname(__file__), "base_apps")


class DisplayPlaylist(Playlist):

    def __init__(
        self,
        frequency: UpdateFrequency,
        items: Optional[List[DisplayItem]] = None,
        app_folders: List[str] = [BASE_APP_PATH]
    ) -> None:
        super().__init__(frequency)
        self._display_info = None
        self._resolve_function = None
        self._display_function = None
        self._apps = self._load_apps(app_folders)
        if items is not None:
            for item in items:
                self.add_item(item)
            self.logger.info(f"Loaded {len(items)} items on playlist start")
        
    @classmethod
    def from_json(cls, path: str, display_obj: DisplayController, app_folders: List[str] = [BASE_APP_PATH]) -> DisplayPlaylist:

        def _load_frequency(frequency: Munch) -> UpdateFrequency:
            return UpdateFrequency(minutes=int(frequency.minutes), seconds=int(frequency.seconds))

        def _load_items(playlist: DisplayPlaylist, items: Munch) -> Tuple[List[DisplayItem], List[str]]:
            output = []
            # Munch reserves "items" keyword - Therefore we use key grabbing
            for item_data in items:
                match DisplayItemType[item_data.item_type.upper()]:
                    case DisplayItemType.STATIC:
                        item = StaticDisplayItem.from_dict(item_data)
                    case DisplayItemType.APP:
                        app_info = playlist.apps.get(item_data.app_name)
                        if hasattr(item_data, "args"):
                            item = app_info.obj(**item_data.args)
                        else:
                            item = app_info.obj()
                    case _:
                        raise TypeError(f"DisplayItemType {item.item_data.upper()} is invalid")
                playlist.add_item(item)
            return output

        if not os.path.exists(path):
            FileNotFoundError(f"{path} does not exist")
        
        if os.path.splitext(path)[-1] != ".json":
            this_type = os.path.splitext(path)[-1]
            raise TypeError(f"Unable to process file type {this_type}")

        with open(path, "r") as file:
            data = munchify(json.load(file))
        frequency = _load_frequency(data.frequency)
        playlist = DisplayPlaylist(
            display_obj=display_obj,
            frequency=frequency, 
        )
        items = _load_items(playlist, data["items"])
        return playlist

    def start(self) -> None:
        if len(self.items) < 1:
            raise PlaylistEmptyError()
        self._time_status = self._update_time_status()
        super().start()

    def update(self) -> None:
        self._time_status = self._update_time_status()
        self.logger.info("Updating")
        if self.current_item.is_alive:
            self.current_item.stop()
        next_item = self.next()
        if next_item is not None:
            self.logger.info(f"Starting next item {next_item.name} {next_item.uuid}")
            next_item.start()

    def add_display_info(self, display_info: DisplayInfo) -> None:
        self.logger.debug("Added display info")
        self._display_info = display_info

    def add_resolve_function(self, function: Callable[Dict[Tuple[int, int], str], Dict[Tuple[int, int]]]):
        self.logger.debug(f"Added resolve function -> {function.__name__}")
        self._resolve_function = function

    def add_display_function(self, function: Callable[Dict[Tuple[int, int], int], None]) -> None:
        self.logger.debug(f"Added display function -> {function.__name__}")
        self._display_function = function

    def add_item(self, item: DisplayItem) -> None:
        self.logger.info(f"Adding item {item.name} to playlist")
        if not isinstance(item, DisplayItem):
            raise TypeError(f"Cannot add {type(item)} to DisplayPlaylist, must be of DisplayItem")
        if self._display_info is None:
            raise RuntimeError("No display info set. Set it with `add_display_info`")
        item.add_display_info(self._display_info)
        if self._resolve_function is None:
            raise RuntimeError("No display function set. Set it with `add_resolve_function`")
        item.add_resolve_function(self._resolve_function)
        if self._display_function is None:
            raise RuntimeError("No display function set. Set it with `add_display_function`")
        item.add_display_function(self._display_function)
        super().add_item(item)
        self.logger.info(f"Items now in queue: {self.items}")
        
    @property
    def apps(self) -> AppLoader:
        return self._apps

    def _load_apps(self, app_folders: str) -> AppLoader:
        return AppLoader(
            desired_class=DisplayItem,
            sources=app_folders
        )

    @property
    def available_apps(self) -> List[str]:
        return self._apps.list()