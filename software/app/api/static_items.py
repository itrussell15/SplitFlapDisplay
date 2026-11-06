import os
import uuid
import time
import json
import logging
import tempfile


from app.api.models.static_items import (
    AddStaticItemResponse, StaticItemRequest, StaticItemResponse, StaticItem, StaticItems
)
from app.api.dependencies import get_database
from .common import exception_response
from control.source.flaps import Flap
import utils

from app.components.display_playlist.base_apps.static import StaticDisplayItem
from fastapi import APIRouter, Depends, HTTPException, Request, status

logger = logging.getLogger("StaticApps")
router = APIRouter(prefix="/static", tags=["Static"])

STATIC_PATH = utils.get_static_item_path()

@router.post("/add", response_model=AddStaticItemResponse)
def add_static_item(request: StaticItemRequest, database = Depends(get_database)):

    output = {"timestamp": time.time()}
    modules = []
    for module in request.module_requests:
        try:
            # Ensure that the flap is valid
            Flap[module.flap]

            modules.append(
                {
                    "location": module.location.as_dict(),
                    "value": module.flap.upper()
                }
            )
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Flap value '{module.flap}' is not valid",
            )
    this_id = str(uuid.uuid4())

    output["name"] = request.name
    output["uuid"] = this_id
    output["cells"] = modules
    
    # Save to database
    with database.connect() as db:
        db.add_static_item(**output)
    
    return AddStaticItemResponse(
        name=request.name,
        uuid=this_id,
        creation_time=request.request_time,
        data=modules
    )

@router.get("/names")
def get_static_item_names(database = Depends(get_database)):
    logger.info("Getting static item names")
    
    with database.connect() as db:
        names = db.get_static_item_names()

    return {"num_items": len(names), "names": names}

@router.get("/uuid", response_model=StaticItem)
def get_item_from_uuid(uuid: str, database = Depends(get_database)):
    logger.info(f"Fetching static item {uuid}")
    try:
        with database.connect() as db:
            item = db.get_item_from_uuid(uuid)
        return item
    except Exception as e:
        raise exception_response(e)

@router.delete("/uuid")
def delete_from_uuid(uuid: str, database = Depends(get_database)):
    logger.info(f"Deleting static item with uuid {uuid}")
    try:
        with database.connect() as db:
            is_ok = db.delete_uuid(uuid)
    except Exception as e:
        raise exception_response(e)
    return {'is_ok': is_ok}
