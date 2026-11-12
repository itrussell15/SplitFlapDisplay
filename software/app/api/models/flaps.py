from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class FlapData(BaseModel):
    position: int
    key: str
    glyph: str
    color_hex: str
    aliases: List[str]

    @property
    def name_map(self) -> Dict[str, FlapData]:
        output = {}
        values = self.aliases + [self.key, self.glyph]
        return {value: self for value in values}
 

class FlapsByPosition(BaseModel):
    num_flaps: int
    flaps: Dict[int, FlapData]


class FlapsByKey(BaseModel):
    num_flaps: int
    flaps: Dict[str, FlapData]

class FlapUpdateRequest(BaseModel):
    position: int
    character: str
    color_hex: str