import sys
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple, Union


sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from app.components.core.trigger import Trigger
from app.components.display.display_item import (
    DisplayItem,
    DisplayItemType,
    DisplayItemUpdate,
)
from control.source.display_controller import DisplayInfo


class StaticDisplayItem(DisplayItem):

    trigger_factory = None
    description: str = "Dead simple display of a static message that has been set from the main Display page."

    def __init__(
        self,
        name: str,
        trigger_factory: Callable[[Callable[[], None]], Trigger],
        flaps: Union[Dict[Tuple[int, int], str], Dict[Tuple[int, int], int]],
        needs_resolving: bool = True,
    ) -> None:
        super().__init__(
            name,
            item_type=DisplayItemType.STATIC,
            params=locals(),
            trigger_factory=trigger_factory,
        )
        self.flaps = flaps
        self._needs_resolving = needs_resolving

    def __repr__(self) -> str:
        return f"StaticDisplayItem({self.name})"

    # TODO Update this to conform to positions based calls
    def update(self, display_info: DisplayInfo) -> DisplayItemUpdate:
        return DisplayItemUpdate(self.flaps, needs_resolving=self._needs_resolving)

    @property
    def needs_resolving(self) -> bool:
        return self._needs_resolving
