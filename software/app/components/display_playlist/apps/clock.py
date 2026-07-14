import sys
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from app.components.core.updater import UpdateFrequency
from app.components.display_playlist.display_item import DisplayItem

class ClockApp(DisplayItem):

    def __init__(self) -> None:
        frequency = UpdateFrequency(seconds = 10)
        super().__init__(
            name="ClockApp",
            frequency=frequency
        ),

    def update(self, display_info: DisplayInfo) -> Dict[Tuple[int, int], str]:
        now = datetime.datetime.now()
        hour = now.strftime("%I").lstrip("0")
        minute = now.strftime("%M")

        # Hour
        data = {(1, 2): hour[-1]}
        if len(hour) > 1:
            data[(1, 1)] = hour[0]
        
        # Minute
        data[(1, 5)] = minute[-1]
        data[(1, 4)] = minute[0]
        data[(1, 3)] = ":"
        
        return data
        


            
            
