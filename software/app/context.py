import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, List

from fastapi import FastAPI, Request

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from control.source.bus_controller import BusController
from control.source.display_controller import DisplayController
from app.components.core.app_loader import AppLoader
from app.components.display_playlist.playlist import DisplayPlaylist
from app.components.display_playlist.display_item import DisplayItem
from app.components.core.rate_limiter import RateLimiter
from app.components.core.updater import UpdateFrequency
import utils


logger = logging.getLogger(__name__)
VARS = utils.get_env_vars()

ROWS = utils.Range(1, int(VARS["DISP_MAX_ROWS"]))
COLUMNS = utils.Range(1, int(VARS["DISP_MAX_COLUMNS"]))
DEFAULT_RATE = {"minutes": 1, "seconds": 0}
APP_PATHS = VARS["DISP_APP_PATHS"]

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # app startup
    logger.info("Initializing App")
    
    # Display Connection
    ports = get_ports()
    logging.getLogger("BusController(/tmp/vcom_host)").setLevel(logging.WARNING)
    logging.getLogger("OutgoingMessage").setLevel(logging.WARNING)
    app.state.display = connect_to_display(ports)
    logger.info(f"Display connected with {app.state.display.num_modules} modules found")

    # App Loading
    logger.info("Loading Apps")
    paths = get_app_paths()
    app.state.app_loader = AppLoader(DisplayItem, sources=paths)
    app.state.playlist = DisplayPlaylist(app.state.display, frequency=UpdateFrequency(seconds=30))
    logger.info(f"Loaded {len(app.state.app_loader)} apps from {len(paths)} path(s)")
    
    
    yield

    # app teardown
    logger.info("Tearing down app")
    app.state.display.close()


def get_ports() -> List[str]:
    value = VARS["DISP_USB_PORT"]
    if value is None:
        raise ConnectionError(f"No port to connect to. Please set a port to connect to with 'export DISP_USB_PORT=<port>'")
    output = []
    for port in value.split(","):
        output.append(value.strip())
    return output

def get_app_paths() -> List[str]:
    value = VARS["DISP_APP_PATHS"]
    if value is None:
        return None
    
    output = []
    for path in value.split(","):
        path = os.path.join(os.getcwd(), path)
        if not os.path.exists(path.strip()):
            raise FileNotFoundError(f"No file path found while loading apps at {path}")
        output.append(path.strip())
    return output

def connect_to_display(ports: List[str]) -> DisplayController:
    display = DisplayController()
    ports = get_ports()
    if ports is None:
        raise ConnectionError(f"No port to connect to. Please set a port to connect to with 'export DISP_USB_PORT=<port>'")
    for port in ports:
        bus = BusController(port=port, timeout=0.5)
        display.add_bus_controller(bus)

    display.discover(ROWS, COLUMNS)
    return display