import logging
from typing import List
from app.api.models.flaps import FlapData

class FlapResolver:

    def __init__(self, flap_data: List[FlapData]) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._flaps = flap_data
        self._map = {}
        for flap in self._flaps:
            self._map.update(flap.name_map)

    def resolve(self, value: str) -> FlapData:
        output = self._map.get(value, None)
        if output is None:
            raise KeyError(f"Unable to resolve '{value}'")
        return output