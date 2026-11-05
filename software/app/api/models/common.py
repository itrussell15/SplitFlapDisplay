from typing import List, Tuple
from pydantic import BaseModel

class Location(BaseModel):
    row: int
    column: int

    def as_tuple(self) -> Tuple[int, int]:
        return (self.row, self.column)

    def as_dict(self) -> Dict[str, int]:
        return {
            "row": self.row,
            "column": self.column
        } 

class LatencyResponse(BaseModel):
    send: float
    receive: float
    total: float

class AverageLatencyResponse(LatencyResponse):
    count: int