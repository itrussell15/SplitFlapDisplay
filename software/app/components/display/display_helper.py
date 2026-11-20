import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from control.source.display_controller import DisplayInfo
from utils import Range

class DisplayRenderError(Exception):
    def __init__(self, error: str) -> None:
        super().__init__(error)

class DisplayHelper:

    def __init__(
        self,
        display_info: DisplayInfo,
        default_flap_position: int = 0,
        default_flap_key: str = "BLANK"
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._info = display_info
        self._default_position = default_flap_position
        self._default_key = default_flap_key
        

    def default_fill(
        self,
        fill_value: Union[int, str],
        incoming_values: Optional[Dict[Tuple[int, int], Union[int, str]]] = None,
    ) -> Dict[Tuple[int, int], Union[int, str]]:
        as_position = isinstance(fill_value, int)
        resolve_as = "position" if as_position else "key"
        self.logger.info(f'Default filling with {resolve_as}')
        output = self._default_fill(
            skip_values=list(incoming_values.keys()) if incoming_values else None,
            rows=self._info.row_range,
            columns=self._info.column_range,
            value=self._default_position if as_position else self._default_key
        )
        output.update(incoming_values)
        return output

    def default_fill_position(self) -> Dict[Tuple[int, int], int]:
        return self.default_fill(self._default_position)

    def default_fill_value(self) -> Dict[Tuple[int, int], str]:
        return self.default_fill(self._default_key)

    def center_row(self, text: str, row_value: int, fill_value: str = "BLANK") -> Dict[Tuple[int, int], str]:
        incoming_size = len(text)
        if incoming_size > self._info.columns:
            raise DisplayRenderError(f"Unable to render text of length {incoming_size}. Display width is {self._info.columns}")

        if row_value < 1 or row_value > self._info.rows:
            raise DisplayRenderError(f"Invalid Row {row_value}, Pick 1-{self._info.rows}")
        
        delta = self._info.columns - incoming_size
        start_position = delta // 2

        output = {}
        for n, char in enumerate(text):
            output[(row_value, n + start_position)] = char
            # print(f"Assigning {char} to {(row_value, n + start_position)}")
        infill = self._default_fill(
            value=fill_value,
            skip_values=output,
            rows=Range(row_value, row_value),
            columns=self._info.column_range
        )
        output.update(infill)

        return output


    def center_rows(self, rows: List[str]) -> Dict[Tuple[int, int], str]:
        if len(rows) != self._info.rows:
            raise ValueError(f"Num rows passed {len(rows)} doesn't match the {self._info.rows} found on display")

        # for row in rows:


    def center_text(self, text: str) -> Dict[Tuple[int, int], str]:
        if text is None:
            return {}
        if not isinstance(text, str):
            raise TypeError(f"Expected text to be str, got {type(text).__name__}")

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.split("\n") if normalized else [""]
        output: Dict[Tuple[int, int], str] = {}

        start_row = max(1, (self._info.rows - len(lines)) // 2 + 1)

        for row_offset, line in enumerate(lines):
            row = start_row + row_offset
            if row > self._info.rows:
                break

            visible_line = line[: self._info.columns]
            if not visible_line:
                continue

            start_col = max(1, (self._info.columns - len(visible_line)) // 2 + 1)
            for col_offset, character in enumerate(visible_line):
                output[(row, start_col + col_offset)] = character

        return output

    def _default_fill(self, value: Any, rows: Range, columns: Range, skip_values: Optional[List[Tuple[int, int]]] = None) -> Dict[Tuple[int, int], Any]:
        if skip_values is None:
            skip_values = []

        output = {}
        for row in rows:
            for column in columns:
                location = (row, column)
                if location in skip_values:
                    continue
                output[(row, column)] = value
        return output