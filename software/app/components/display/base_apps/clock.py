import datetime
import os
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from app.components.core.trigger import IntervalTrigger, Trigger
from app.components.core.updater import UpdateFrequency
from app.components.display.display_helper import DisplayHelper
from app.components.display.display_item import (
    DisplayItem,
    DisplayItemType,
    DisplayItemUpdate,
)
from control.source.display_controller import DisplayInfo


class DateTimeApp(DisplayItem):

    description = "Basic clock app that shows the current time"
    app_image = "static/images/clock-icon.png"

    @classmethod
    def trigger_factory(cls, callback: Callable[[], None]) -> Trigger:
        return IntervalTrigger(callback, frequency=UpdateFrequency(seconds=5))

    def __init__(
        self,
        trigger_factory: Optional[Callable[[Callable[[], None]], Trigger]],
        start_location: List[int] = [1, 1],
    ) -> None:
        super().__init__(
            name="DateTimeApp",
            item_type=DisplayItemType.APP,
            trigger_factory=trigger_factory,
            params=locals(),
        )
        self._previous_output = None
        if isinstance(start_location, str):
            self.logger.info(f"Parsing start location string - {start_location}")
            start_location = [int(i) for i in start_location.split(",")]
        self.logger.info(f"Started with start location {start_location}")
        self._start_location = start_location

    def update(self, display_info: DisplayInfo) -> DisplayItemUpdate:
        helper = DisplayHelper(display_info)
        now = datetime.datetime.now()
        date = now.strftime("%b %d %Y")
        weekday = now.strftime("%A")
        time = now.strftime("%I:%M%p")
        if time.startswith("0"):
            time = " " + time[1:]

        final = date + "\n" + weekday + "\n" + time
        self.logger.info(f"Final display output - {final}")
        flaps = helper.center_text(final.upper())
        flaps = helper.default_fill(fill_value="BLANK", incoming_values=flaps)

        if time == self._previous_output:
            self.logger.debug("Same time as last update")

        self.logger.info(f"Showing {final}")
        self._previous_output = final
        return DisplayItemUpdate(flaps=flaps, needs_resolving=True)
