import datetime
import logging
import time

from typing import Any, Callable, Optional

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
