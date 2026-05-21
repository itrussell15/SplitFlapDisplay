from datetime import datetime
import logging
import serial
import time
from typing import Optional

# Functions
def create_logger(level = logging.DEBUG, spacing: int = 15):
    logging.basicConfig(
        level=level,
        format=f'[%(levelname)-8s][%(name)-{spacing}s] %(message)s',
        datefmt='%H:%M:%S'
    )

def get_current_timestamp() -> str:
    TIMESTAMP_FORMAT = "%Y_%m_%d-%H_%M_%S"
    return datetime.now().strftime(TIMESTAMP_FORMAT)
