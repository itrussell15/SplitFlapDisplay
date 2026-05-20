import logging
from fastapi import APIRouter, Request

API_VERSION = "v1"
RELEASE_VERSION = "1.0"

router = APIRouter(
    prefix=f"/{API_VERSION}",
)

logger = logging.getLogger("BaseAPI")
logger.info("Started")

@router.get(f"/health")
async def health_check(request: Request):
    logger.info(request.app.state.foo)
    return {"status": "online"}

@router.get(f"/version")
async def release_version(request: Request):
    return {"version": RELEASE_VERSION}