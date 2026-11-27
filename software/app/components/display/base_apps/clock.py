import datetime
import os
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from app.components.core.trigger import IntervalTrigger, PollingTrigger, Trigger
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
        return PollingTrigger(callback, frequency=UpdateFrequency(seconds=1))

    def __init__(
        self,
        trigger_factory: Optional[Callable[[Callable[[], None]], Trigger]],
    ) -> None:
        super().__init__(
            name="DateTimeApp",
            item_type=DisplayItemType.APP,
            trigger_factory=trigger_factory,
            params=locals(),
        )
        self._previous_output = None
        self._current_output = self._generate_display_text()

    def should_update(self) -> bool:
        """
        Will update if the current output doesn't equal the previous output
        """
        self._current_output = self._generate_display_text()
        return self._current_output != self._previous_output

    def update(self, display_info: DisplayInfo) -> DisplayItemUpdate:
        """
        This function only gets hit if `should_update` evaluates to True
        """
        self.logger("Update triggered")
        helper = DisplayHelper(display_info)
        self.logger.info(f"Final display output - {self._current_output}")
        flaps = helper.center_text(self._current_output.upper())
        flaps = helper.default_fill(fill_value="BLANK", incoming_values=flaps)

        self._previous_output = self._current_output
        return DisplayItemUpdate(flaps=flaps, needs_resolving=True)

    @staticmethod
    def _generate_display_text() -> str:
        now = datetime.datetime.now()
        date = now.strftime("%b %d %Y")
        weekday = now.strftime("%A")
        time = now.strftime("%I:%M%p")
        if time.startswith("0"):
            time = " " + time[1:]

        return date + "\n" + weekday + "\n" + time