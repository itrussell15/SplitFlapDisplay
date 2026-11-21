import os
import datetime
import enum
import sys
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from app.components.core.trigger import IntervalTrigger, Trigger
from app.components.core.updater import UpdateFrequency
from app.components.display.display_item import (
    DisplayItem,
    DisplayItemType,
    DisplayItemUpdate,
)
from app.components.display.display_helper import DisplayHelper
from control.source.display_controller import DisplayInfo
from utils import ApiKeyError

API_KEY_NAME: str = "OPEN_WEATHER_API_KEY"

@dataclass
class WeatherData:

    temp: float
    feels_like: float
    wind_speed: float
    uvi: float
    clouds: float
    humidity: float
    sunrise: int
    sunset: int
    overview: str
    description: str
    timezone: str
    unit: str
    extra: dict[str, Any] = None  # Optional: store leftover kwargs

    @classmethod
    def from_kwargs(cls, **kwargs):
        known_fields = {f.name for f in fields(cls)}
        known_args = {k: v for k, v in kwargs.items() if k in known_fields}
        extra_args = {k: v for k, v in kwargs.items() if k not in known_fields}
        
        # Pass extra_args if you want to save them, or omit to ignore them
        return cls(**known_args, extra=extra_args)

    def __post_init__(self) -> None:

        for key, value in locals().items():
            if key != "kwargs":
                setattr(
                    self, key, value if not isinstance(value, float) else int(value)
                )
        self.timezone = ZoneInfo(self.timezone)
        self.sunrise = datetime.datetime.fromtimestamp(self.sunrise, tz=self.timezone)
        self.sunset = datetime.datetime.fromtimestamp(self.sunset, tz=self.timezone)


REQUEST_URL = "https://api.openweathermap.org/data/4.0/onecall/current?lat={lat}&lon={lon}&units={units}&appid={api_key}"


class TemperatureApp(DisplayItem):

    description = "Weather App that pulls data from Open Weather Map"
    app_image = "static/images/temperature-icon.png"

    # TODO Add rate limiter?
    # TODO Add env variable for API key?

    @classmethod
    def trigger_factory(cls, callback: Callable[[], None]) -> Trigger:
        return IntervalTrigger(callback, frequency=UpdateFrequency(seconds=60))

    def __init__(
        self,
        trigger_factory: Optional[Callable[[Callable[[], None]], Trigger]],
        lat: str,
        lon: str,
        metric_units: bool = False,
    ) -> None:
        super().__init__(
            name="TempApp",
            item_type=DisplayItemType.APP,
            trigger_factory=trigger_factory,
            params=locals(),
        )
        self._api_key = os.getenv(API_KEY_NAME, None)
        if self._api_key is None:
            raise ApiKeyError(API_KEY_NAME)
        self.lat_value = lat
        self.long_value = lon

        # TODO Fix unit parsing
        if isinstance(metric_units, str):
            metric_units = metric_units.strip().lower() in {"true", "1", "yes", "metric", "celsius", "c"}
        self._unit_system = "metric" if bool(metric_units) else "imperial"

    def get_data(self) -> WeatherData:
        units = self._unit_system
        url = REQUEST_URL.format(
            lat=self.lat_value,
            lon=self.long_value,
            units=units,
            api_key=self._api_key,
        )
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            raise ConnectionError()

        body = r.json()
        data = body["data"][0]
        return WeatherData.from_kwargs(
            **data,
            unit=units,
            timezone=body["timezone"],
            overview=data["weather"][0]["main"],
            description=data["weather"][0]["description"],
        )

    def get_sun_times(
        self,
        helper: DisplayHelper,
        sunrise: datetime.datetime,
        sunset: datetime.datetime,
        row: int = 1
    ) -> Dict[Tuple[int, int], str]:
        sunset = sunset.strftime("%I:%M") 
        if sunset.startswith("0"):
            sunset = sunset[1:]

        sunrise = sunrise.strftime("%I:%M") 
        if sunrise.startswith("0"):
            sunrise = sunrise[1:]

        sunrise = f"☀↑{sunrise.strip()}"
        sunset = f"☀↓{sunset.strip()}"
        final = sunrise + " " + sunset
        self.logger.info(f"Sun times - {final}")

        return helper.center_row(row_value=1, fill_value="BLANK", text=final)

    def get_temperature_data(
        self,
        helper: DisplayHelper,
        temp: float,
        is_metric: bool,
        row_value: int
    ) -> Dict[Tuple[int, int], str]:
        if isinstance(is_metric, str):
            is_metric = is_metric.strip().lower() in {"true", "1", "yes", "metric", "celsius", "c"}
        numeric_temp = int(temp)
        unit = "C" if bool(is_metric) else "F"
        final = f"{numeric_temp}°{unit}"
        self.logger.info(f"Temp - {final}")
        return helper.center_row(row_value=row_value, fill_value="BLANK", text=final)


    def update(self, display_info: DisplayInfo) -> DisplayItemUpdate:
        helper = DisplayHelper(display_info)
        weather = self.get_data()
        flaps = self.get_sun_times(
            helper=helper,
            sunset=weather.sunset,
            sunrise=weather.sunrise,
            row=1
        )
        temp_data = self.get_temperature_data(
            helper,
            weather.temp,
            weather.unit == 'metric',
            row_value = 2
        )
        flaps.update(temp_data)
        description = helper.center_row(text=weather.overview.upper(), row_value=3, fill_value="BLANK")
        flaps.update(description)

        return DisplayItemUpdate(flaps=flaps)
