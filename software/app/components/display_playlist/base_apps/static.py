import os
import sys
from munch import munchify
from pathlib import Path
from typing import Dict, Tuple


sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from app.components.display_playlist.display_item import DisplayItem, DisplayItemType
from control.source.display_controller import DisplayInfo

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

    # TODO Update this to conform to positions based calls
    def update(self, display_info: DisplayInfo) -> Dict[Tuple[int, int], str]:
        return self.flaps