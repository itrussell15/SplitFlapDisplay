from typing import List, Tuple
from pydantic import BaseModel

class Location(BaseModel):
    row: int
    column: int

    def as_tuple(self) -> Tuple[int, int]:
        return (self.row, self.column)