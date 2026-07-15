import sys
import json
from pathlib import Path
from typing import Any, Callable, Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from app.components.core.updater import UpdateFrequency
from app.components.core.playlist import Playlist

class DisplayPlaylist(Playlist):

    def __init__(self, display_obj: DisplayController, frequency: UpdateFrequency) -> None:
        super().__init__(frequency)
        self._display = display_obj

    @classmethod
    def static_from_json(self, path: str) -> DisplayPlaylist:
        if not os.path.exists(path):
            FileNotFoundError(f"{path} does not exist")
        
        if os.path.splitext(path)[-1] != ".json":
            this_type = os.path.splitext(path)[-1]
            raise TypeError(f"Unable to process file type {this_type}")

        with open(path, "r") as file:
            data = json.load(file)
        
    def update(self) -> None:
        if self.current_item.is_alive:
            self.current_item.stop()
        next_item = self.next()
        if next_item is not None:
            next_item.start()

    def add_item(self, item: PlaylistItem) -> None:
        super().add_item(item)
        item.add_display_info(self._display.info)
        item.add_display_function(self._display.move_to_flaps)

if __name__ == "__main__":
    import os
    from utils import create_logger
    create_logger()

    from app.components.display_playlist.display_item import DisplayItem, StaticDisplayItem
    from control.source.bus_controller import BusController
    from control.source.display_controller import DisplayController
    from app.components.display_playlist.apps.clock import ClockApp

    # playlist = DisplayPlaylist.static_from_json("/home/isaac/projects/SplitFlapDisplay/software/app/components/display_playlist/examples/playlist.json")
    # print(playlist)

    display = DisplayController()
    value = os.getenv("DISP_USB_PORT")
    bus = BusController(port=value, timeout=0.5)
    display.add_bus_controller(bus)
    display.discover([1, 2], [1, 10])

    playlist_frequency = UpdateFrequency(seconds = 10)
    playlist = DisplayPlaylist(display, playlist_frequency)

    item1 = StaticDisplayItem.from_json("/home/isaac/projects/SplitFlapDisplay/software/app/components/display_playlist/examples/static_example_symbols1.json")
    item2 = StaticDisplayItem.from_json("/home/isaac/projects/SplitFlapDisplay/software/app/components/display_playlist/examples/static_example_symbols2.json")
    item3 = StaticDisplayItem.from_json("/home/isaac/projects/SplitFlapDisplay/software/app/components/display_playlist/examples/static_example_symbols3.json")

    playlist.add_item(item1)
    playlist.add_item(item2)
    playlist.add_item(item3)
    playlist.add_item(ClockApp())

    playlist.start()