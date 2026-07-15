import sys
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from app.components.core.updater import UpdateFrequency
from app.components.display_playlist.display_item import DisplayItem

class ClockApp(DisplayItem):

    def __init__(self, start_location: Tuple[int, int]) -> None:
        frequency = UpdateFrequency(seconds = 10)
        super().__init__(
            name="ClockApp",
            frequency=frequency
        )
        self._previous_time = None
        self._start_location = start_location

    def update(self, display_info: DisplayInfo) -> Dict[Tuple[int, int], str]:
        now = datetime.datetime.now()
        hour = now.strftime("%I").lstrip("0")
        minute = now.strftime("%M")
        time = f"{hour}:{minute}"
        if time == self._previous_time:
            self.logger.debug("Same time as last update")

        row, start_col = self._start_location
        
        # Hour
        if len(hour) > 1:
            data[(row, start_col)] = hour[0]
        data = {(row, start_col + 1): hour[-1]}

        # Minute
        data[(row, start_col + 3)] = minute[0]
        data[(row, start_col + 4)] = minute[-1]

        data[(row, start_cal + 2)] = ":"
        
        self.logger.info(f"Showing: {hour}:{minute}")
        self._previous_time = time
        return data
        


            
            
