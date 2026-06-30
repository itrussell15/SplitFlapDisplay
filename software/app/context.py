import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, List

from fastapi import FastAPI, Request

sys.path.insert(0, str(Path(__file__).parent.parent))
from control.source.bus_controller import BusController
from control.source.display_controller import DisplayController


logger = logging.getLogger(__name__)

ROWS = [1, 2]
COLUMNS = [1, 10]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # app startup
    logger.info("Initializing App")
    app.state.display = DisplayController()
    for port in get_ports():
        logger.info(f"Adding port {port}")
        bus = BusController(port=port, timeout=0.5)
        app.state.display.add_bus_controller(bus)
    app.state.display.discover(ROWS, COLUMNS)
    logger.info(f"App started with {app.state.display.num_modules} modules found")

    yield

    # app teardown
    logger.info("Tearing down app")
    app.state.display.close()

def get_ports() -> List[str]:
    value = os.getenv("DISP_USB_PORT")
    output = []
    for port in value.split(","):
        output.append(value.strip())
    return output