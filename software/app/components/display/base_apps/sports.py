import os
import sys
from pathlib import Path
import datetime
import requests
from dataclasses import dataclass, fields
from zoneinfo import ZoneInfo
from typing import Any, Callable, Dict, List, Optional, Tuple

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


@dataclass(kw_only=True)
class GenericResponse:
    extra: dict[str, Any] = None  # Optional: store leftover kwargs

    @classmethod
    def from_kwargs(cls, **kwargs):
        known_fields = {f.name for f in fields(cls)}
        known_args = {k: v for k, v in kwargs.items() if k in known_fields}
        extra_args = {k: v for k, v in kwargs.items() if k not in known_fields}
        
        # Pass extra_args if you want to save them, or omit to ignore them
        return cls(**known_args, extra=extra_args)


@dataclass
class NextEventResponse(GenericResponse):
    shortName: str
    date: datetime.datetime
    competitions: List[Any]
    timezone: ZoneInfo

    def __post_init__(self) -> None:
        self.date = datetime.datetime.fromisoformat(self.date).astimezone(self.timezone)

    @property
    def  broadcast(self) -> Optional[str]:
        if len(self.competitions) < 1:
            return None
        competition = self.competitions[0]
        broadcasts = competition["broadcasts"]
        if len(broadcasts) < 1:
            return None
        
        return broadcasts[0]["media"]["shortName"]

@dataclass
class TeamResponse(GenericResponse):
    nextEvent: Dict[str, NextEventResponse]
    record: Dict[str, Any]
    timezone: ZoneInfo

    def __post_init__(self) -> None:
        self.nextEvent = NextEventResponse.from_kwargs(timezone=self.timezone, **self.nextEvent[0]) if len(self.nextEvent) > 0 else self.nextEvent

class EspnRequester:

    BASE_URL = "http://site.api.espn.com/apis/site/v2/sports"
    trigger_factory = None

    class SportHandler:
        def __init__(self, url: str, timezone: ZoneInfo) -> None:
            self.url = url
            self.timezone = timezone

        def _request(self, url: str):
            response = requests.get(url)
            if response.status_code != 200:
                raise ConnectionError(f"Non-200 status code returned from {url}")
            return response.json()

        def get_team(self, team: str):
            response = self._request(f"{self.url}/teams/{team}")
            return TeamResponse.from_kwargs(timezone=self.timezone, **response["team"])

        def get_teams(self):
            return self._request(f"{self.url}/teams")
    
    def __init__(self, timezone: ZoneInfo = ZoneInfo("America/Los_Angeles")) -> None:
        self._sports = {
            "NCAA": self.SportHandler(url=f"{self.BASE_URL}/football/college-football", timezone=timezone),
            "NHL": self.SportHandler(url=f"{self.BASE_URL}/hockey/nhl", timezone=timezone),
            "NFL": self.SportHandler(url=f"{self.BASE_URL}/football/nfl", timezone=timezone),
            "NBA": self.SportHandler(url=f"{self.BASE_URL}/basketball/nba", timezone=timezone),
            "MLB": self.SportHandler(url=f"{self.BASE_URL}/baseball/mlb", timezone=timezone),
        }

    def __getattr__(self, sport: str) -> SportHandler:
        if sport.upper() not in self._sports:
            raise ValueError(f"{sport} is an invalid sport - select one of {self._sports.keys()}")
        return self._sports[sport.upper()]
        

class UpcomingGameApp(DisplayItem):

    description = "Fetch Upcoming Event Info About Your Favorite Sports Team"
    app_image = "static/images/sports.png"
    trigger_factory = None

    def __init__(
        self,
        sport: str,
        team_abbreviation: str,
        trigger_factory: Optional[Callable[[Callable[[], None]], Trigger]],
    ) -> None:
        super().__init__(
            name="UpcomingGameApp",
            item_type=DisplayItemType.APP,
            trigger_factory=trigger_factory,
            params=locals(),
        )
        espn = EspnRequester()
        self._team = team_abbreviation.upper()
        self._handler = getattr(espn, sport)

    def update(self, display_info: DisplayInfo) -> DisplayItemUpdate:
        helper = DisplayHelper(display_info)
        team_data = self._handler.get_team(self._team)

        flaps = {}
        event_desc = helper.center_row(row_value=1, text=team_data.nextEvent.shortName.strip())
        flaps.update(event_desc)

        time = team_data.nextEvent.date.strftime("%I:%M%p")
        if time.startswith("0"):
            time = time[1:]
        date = team_data.nextEvent.date.strftime("%m/%d")
        final = date + " " + time
        game_time = helper.center_row(
            text=final,
            row_value=2, 
        )
        flaps.update(game_time)

        if team_data.nextEvent.broadcast:
            game_channel = helper.center_row(row_value=3, text=team_data.nextEvent.broadcast)
            flaps.update(game_channel)
        
        return DisplayItemUpdate(flaps=flaps, needs_resolving=True)

        
        

        