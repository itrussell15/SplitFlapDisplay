import sys
from pathlib import Path
import logging
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from typing import AsyncGenerator

sys.path.insert(0, str(Path(__file__).parent.parent))
from control.source.display_controller import DisplayController


logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # app startup
    logger.info("Here")
    app.state.foo = "bar"
    yield
    # app teardown