import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from control.source.display_controller import DisplayInfo
from app.components.display.base_apps.weather import TemperatureApp


if __name__ == "__main__":

    app = TemperatureApp(
        trigger_factory=None, lat="47.6062", lon="122.3321"
    )
    display_info = DisplayInfo(rows=3, columns=15, modules=[])
    app.update(display_info)