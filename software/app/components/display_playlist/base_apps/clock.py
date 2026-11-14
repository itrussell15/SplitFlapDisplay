import os
import sys
import datetime
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from app.components.core.updater import UpdateFrequency
from app.components.display_playlist.display_item import DisplayItem, DisplayItemType, DisplayItemUpdate
from control.source.display_controller import DisplayInfo

class ClockApp(DisplayItem):

    description = "Basic clock app that shows the current time"
    app_image = "static/images/clock-icon.png"

    def __init__(self, start_location: List[int] = [1, 1]) -> None:
        frequency = UpdateFrequency(seconds = 10)

        super().__init__(
            name="ClockApp",
            item_type=DisplayItemType.APP,
            frequency=frequency,
            params = locals()
        )
        self._previous_time = None
        if isinstance(start_location, str): 
            self.logger.info(f"Parsing start location string - {start_location}")
            start_location = [int(i) for i in start_location.split(",")]
        self.logger.info(f"Started with start location {start_location}")
        self._start_location = start_location


    def update(self, display_info: DisplayInfo) -> DisplayItemUpdate:
        now = datetime.datetime.now()
        hour = now.strftime("%I").lstrip("0")
        minute = now.strftime("%M")
        time = f"{hour}:{minute}"
        if time == self._previous_time:
            self.logger.debug("Same time as last update")

        row, start_col = self._start_location
        
        data = {}
        # Hour
        if len(hour) > 1:
            data[(row, start_col)] = hour[0]
        data[(row, start_col + 1)] = hour[-1]

        # Minute
        data[(row, start_col + 3)] = minute[0]
        data[(row, start_col + 4)] = minute[-1]

        data[(row, start_col + 2)] = ":"
        
        self.logger.info(f"Showing: {hour}:{minute}")
        self._previous_time = time
        return data
        


            
            
