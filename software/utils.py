import os
import datetime
import logging
import time

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


def get_env_vars() -> Dict[str, str]:
    output: Dict[str, str] = {}
    VARS = ["DISP_MAX_ROWS", "DISP_MAX_COLUMNS", "DISP_USB_PORT"]
    for var in VARS:
        value = os.getenv(var)
        if value is None:
            raise ValueError(f"Environment variable {var} was not set. Please set it with 'export {var}=<value>'")
        output[var] = value
    return output