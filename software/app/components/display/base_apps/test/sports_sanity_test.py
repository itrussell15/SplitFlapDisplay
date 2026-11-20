import pprint
import requests
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from control.source.display_controller import DisplayInfo
from app.components.display.base_apps.sports import EspnRequester


if __name__ == "__main__":
    url = "https://`site.api.espn.com/apis/site/v2/sports/football/college-football/teams/BOIS"
    api_key = 123

    response = requests.get(url)

    if response.status_code == 200:
        pass
        # pprint.pprint(response.json()["team"].keys(), indent=2)
        # pprint.pprint(response.json()["team"]["nextEvent"], indent=2)
    else:
        print(f"Request failed with status code: {response.status_code}")


    espn = EspnRequester()
    # print(espn.ncaa.get_team("BOIS").nextEvent.broadcast)
    # print(espn.nhl.get_teams())
