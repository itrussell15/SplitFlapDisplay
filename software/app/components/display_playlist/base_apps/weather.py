import sys
import enum
import requests
import datetime
from zoneinfo import ZoneInfo
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from app.components.core.updater import UpdateFrequency
from app.components.display_playlist.display_item import DisplayItem, DisplayItemType

class WeatherData:

    def __init__(
        self,
        temp: float,
        feels_like: float,
        wind_speed: float,
        uvi: float,
        clouds: float,
        humidity: float,
        sunrise: int,
        sunset: int,
        overview: str,
        description: str,
        timezone: str,
        unit: str,
        **kwargs
    ) -> None:

        for key, value in locals().items():
            if key != "kwargs":
                setattr(self, key, value if not isinstance(value, float) else int(value))
        self.timezone = ZoneInfo(self.timezone)
        self.sunrise = datetime.datetime.fromtimestamp(self.sunrise, tz=self.timezone)
        self.sunset = datetime.datetime.fromtimestamp(self.sunset, tz=self.timezone)

REQUEST_URL = "https://api.openweathermap.org/data/4.0/onecall/current?lat={lat}2&lon=-{lon}&units={units}&appid={api_key}"

class TemperatureApp(DisplayItem):

    # TODO Add rate limiter?
    # TODO Add env variable for API key?

    def __init__(self, api_key: str, lat: str, lon: str, metric_units: bool = False) -> None:
        frequency = UpdateFrequency(seconds = 60)
        super().__init__(
            name="TempApp",
            item_type=DisplayItemType.APP,
            frequency=frequency
        )
        self._api_key = api_key
        self.lat_value = lat
        self.long_value = lon
        self._metric_units = metric_units

    def get_data(self):
        units = "metric" if self._metric_units else "imperial"
        url = f"https://api.openweathermap.org/data/4.0/onecall/current?lat={self.lat_value}2&lon=-{self.long_value}&units={units}&appid={self._api_key}"
        r = requests.get(url)
        if r.status_code != 200:
            raise ConnectionError()

        body = r.json()
        data = body["data"][0]
        return WeatherData(
            **data,
            unit=units,
            timezone=body["timezone"],
            overview=data["weather"][0]["main"],
            description=data["weather"][0]["description"],
        )

    def update(self, display_info: DisplayInfo) -> Dict[Tuple[int, int], str]:
        weather = self.get_data()

        data = {}
        temp = str(weather.temp)
        if len(temp) > 1:
            data[(1, 1)] = temp[0]
        data[(1, 2)] = temp[-1]
        data[(1, 3)] = "DEGREE"
        data[(1, 4)] = "F" if weather.unit == "imperial" else "C"

        return data
        