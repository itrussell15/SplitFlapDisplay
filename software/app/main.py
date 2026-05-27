import os
import sys
from pathlib import Path
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).parent.parent))
print(sys.path)
from app.context import lifespan
from app.api.base import API_VERSION
from app.api import display, base, module
from app.frontend import frontend
from utils import create_logger


create_logger()
logger = logging.getLogger(__name__)
app = FastAPI(lifespan=lifespan)

base_dir = os.path.join(os.getcwd(), "app")

app.include_router(frontend.router)
app.include_router(base.router, prefix=f"/api")
app.include_router(display.router, prefix=f"/api/{API_VERSION}")
app.include_router(module.router, prefix=f"/api/{API_VERSION}")
app.mount("/", StaticFiles(directory=os.path.join(base_dir, "frontend"), html=True), name="frontend")
