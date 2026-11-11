import os
import datetime
import logging
import time
from dataclasses import dataclass

from typing import Any, Callable, Optional, Dict

import serial

TIMESTAMP_FORMAT = "%m/%d/%Y %H:%M:%S"

# Functions
def create_logger(level=logging.DEBUG, spacing: int = 15):
    logging.basicConfig(
        level=level,
        format=f"[%(levelname)-8s][%(name)-{spacing}s] %(message)s",
        datefmt="%H:%M:%S",
    )
    

def get_current_timestamp() -> str:
    return datetime.datetime.now().strftime(TIMESTAMP_FORMAT)

def get_env_var(var: str, default: Optional[str] = None) -> str:
    value = os.getenv(var)
    if value is None:
        if default is None:
            raise ValueError(f"Environment variable {var} was not set. Please set it with 'export {var}=<value>'")
        else:
            return default
    return value

def get_env_path(var: str, fail_if_missing: bool = True) -> str:
    path = os.getenv(var)
    if not os.path.exists(path) and fail_if_missing:
        raise FileNotFoundError(f"{path} was not found")
    return path

def get_database_path() -> str:
    return get_env_path("DISP_DB", fail_if_missing=False)

def get_all_env_vars() -> Dict[str, str]:
    output: Dict[str, str] = {}
    VARS = [
        "DISP_MAX_ROWS",
        "DISP_MAX_COLUMNS",
        "DISP_USB_PORT",
        "DISP_APP_PATHS",
        "DISP_NUM_FLAPS"
    ]
    for var in VARS:
        output[var] = get_env_var(var)
    return output

@dataclass(frozen=True)
class Range:
    min: int
    max: int

    def __post_init__(self) -> None:
        if self.min > self.max:
            raise ValueError(f"Range is invalid. Min > Max")

    def __iter__(self) -> None:
        for i in range(self.min, self.max + 1):
            yield i

    @property
    def delta(self) -> int:
        return (self.max + 1) - self.min

        