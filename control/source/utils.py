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


