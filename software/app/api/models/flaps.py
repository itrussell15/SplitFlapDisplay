from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class FlapData(BaseModel):
    position: int
    key: str
    glyph: str
    color_hex: str


class AllFlaps(BaseModel):
    num_flaps: int
    flaps: Dict[int, FlapData]


class FlapUpdateRequest(BaseModel):
    position: int
    character: str
    color_hex: str