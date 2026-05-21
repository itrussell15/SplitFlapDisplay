import logging
import time
from datetime import datetime
from typing import Optional

import serial

TIMESTAMP_FORMAT = "%Y_%m_%d-%H_%M_%S"


# Functions
def create_logger(level=logging.DEBUG, spacing: int = 15):
    logging.basicConfig(
        level=level,
        format=f"[%(levelname)-8s][%(name)-{spacing}s] %(message)s",
        datefmt="%H:%M:%S",
    )


def get_current_timestamp() -> str:
    return datetime.now().strftime(TIMESTAMP_FORMAT)
