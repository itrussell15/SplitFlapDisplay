import os
import sys
import json
from munch import munchify
from pathlib import Path
from typing import Any, Callable, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from app.components.core.updater import UpdateFrequency
from app.components.core.playlist import Playlist, PlaylistItem
from app.components.core.app_loader import AppLoader
from app.components.display_playlist.display_item import DisplayItem, DisplayItemType, StaticDisplayItem

BASE_APP_PATH = os.path.join(os.path.dirname(__file__), "base_apps")


class DisplayPlaylist(Playlist):

    def __init__(
        self,
        display_obj: DisplayController,
        frequency: UpdateFrequency,
        items: Optional[List[DisplayItem]] = None,
        app_folders: List[str] = [BASE_APP_PATH]
    ) -> None:
        super().__init__(frequency)
        self._display = display_obj
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

    def update(self) -> None:
        if self.current_item.is_alive:
            self.current_item.stop()
        next_item = self.next()
        if next_item is not None:
            next_item.start()

    def add_item(self, item: DisplayItem) -> None:
        if not isinstance(item, DisplayItem):
            raise TypeError(f"Cannot add {type(item)} to DisplayPlaylist, must be of DisplayItem")
        super().add_item(item)
        item.add_display_info(self._display.info)
        item.add_display_function(self._display.move_to_flaps)

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

if __name__ == "__main__":
    import os
    from utils import create_logger
    create_logger()

    from app.components.display_playlist.display_item import DisplayItem, StaticDisplayItem
    from control.source.bus_controller import BusController
    from control.source.display_controller import DisplayController
    from app.components.display_playlist.base_apps.clock import ClockApp

    display = DisplayController()
    value = os.getenv("DISP_USB_PORT")
    bus = BusController(port=value, timeout=0.5)
    display.add_bus_controller(bus)
    display.discover([1, 2], [1, 10])

    playlist = DisplayPlaylist.from_json(
        path="/home/isaac/projects/SplitFlapDisplay/software/app/components/display_playlist/examples/playlist.json",
        display_obj=display,
        app_folders=["/home/isaac/projects/SplitFlapDisplay/software/app/components/display_playlist/other_apps", BASE_APP_PATH]
    )
    
    # item1 = StaticDisplayItem.from_json("/home/isaac/projects/SplitFlapDisplay/software/app/components/display_playlist/examples/static_example_symbols1.json")
    # item2 = StaticDisplayItem.from_json("/home/isaac/projects/SplitFlapDisplay/software/app/components/display_playlist/examples/static_example_symbols2.json")
    # item3 = StaticDisplayItem.from_json("/home/isaac/projects/SplitFlapDisplay/software/app/components/display_playlist/examples/static_example_symbols3.json")

    # playlist.add_item(item1)
    # playlist.add_item(item2)
    # playlist.add_item(item3)
    # playlist.add_item(ClockApp())

    playlist.start()