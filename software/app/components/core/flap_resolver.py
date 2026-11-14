import logging
from typing import Dict, List, Tuple
from app.api.models.flaps import FlapData

class ResolutionError(Exception):
    pass

class FlapResolver:

    def __init__(self, flap_data: List[FlapData], default_flap_data_position: int = 0) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        assert isinstance(flap_data, list), f"Flap data passed in was not list, but rather {type(flap_data)}"
        if len(flap_data) < 1:
            raise ValueError("No data found in flap_data parameter")
        self._flaps = flap_data
        self._map = {}
        self._positions = {}
        for n, flap in enumerate(self._flaps):
            assert isinstance(flap, FlapData), f"Value passed in was not FlapData, but rather {type(flap)}"
            self._map.update(flap.name_map)
            self._positions[flap.position] = flap
        self._default_flap_data = flap_data[default_flap_data_position]

    def resolve_value(self, value: str, fail_if_not_found: bool = False) -> FlapData:
        output = self._map.get(value, None)
        if output is None:
            if fail_if_not_found:
                raise ResolutionError(f"Unable to resolve '{value}'")
            else:
                output = self._default_flap_data
        return output

    def resolve_position(self, position: int) -> FlapData:
        output = self._positions.get(position, None)
        if output is None:
            raise ResolutionError(f"Unable resolve position {position}")
        return output

    def resolve(self, values: Dict[Tuple[int, int], str], fail_if_not_found: bool = False) -> Dict[Tuple[int, int], int]:
        output = {}
        for location, value in values.items():
            output[location] = self.resolve_value(value)
        return output
