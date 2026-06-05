import os
import sys
import logging
from pathlib import Path
from source.bus_controller import BusController

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import create_logger

logger = logging.getLogger("main")

def init() -> None:
    
    ports = os.getenv("DISP_USB_PORT")

    buses = []
    for port in ports.split(","):
        port = port.strip()
        logging.info(f"Searching for bus on {port}")
        buses.append(BusController(port=port))

if __name__ == "__main__":
    create_logger()
    init()