import sys
from pathlib import Path
import logging
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from typing import AsyncGenerator

sys.path.insert(0, str(Path(__file__).parent.parent))
from control.source.bus_controller import BusController
from control.source.display_controller import DisplayController


logger = logging.getLogger(__name__)
PORTS = ["/dev/ttyACM1"]
NUM_ROWS = 2
NUM_COLUMNS = 3


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # app startup
    logger.info("Initializing App")
    app.state.display = DisplayController()
    for port in PORTS:
        bus = BusController(port=port, timeout=0.5)
        app.state.display.add_bus_controller(bus)
    app.state.display.discover(NUM_ROWS, NUM_COLUMNS)
    logger.info(f"App started with {app.state.display.num_modules} modules found")
    
    yield
    
    # app teardown
    logger.info("Tearing down app")
    app.state.display.close()