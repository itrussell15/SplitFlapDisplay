import os
import uuid
import time
import json
import logging
import tempfile

from app.api.models.static_items import (
    AddStaticItemResponse, StaticItemRequest, StaticItemResponse, StaticItems
)

from control.source.flaps import Flap
import utils

from app.components.display_playlist.base_apps.static import StaticDisplayItem
from fastapi import APIRouter, Depends, HTTPException, Request, status

logger = logging.getLogger("StaticApps")
router = APIRouter(prefix="/static", tags=["Integrations", "Apps", "Static"])

STATIC_PATH = utils.get_static_item_path()

@router.post("/add", response_model=AddStaticItemResponse)
def add_static_item(request: StaticItemRequest):
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
    output["data"] = modules
    
    # Store static location
    file_name = f"{this_id}.json"
    if file_name in os.listdir(STATIC_PATH):
        raise FileExistsError(f"{file_name} alerady exists in static path")
    
    path = os.path.join(STATIC_PATH, file_name)
    with open(path, "w") as f:
        json.dump(output, f, indent=2)
    
    return AddStaticItemResponse(
        name=request.name,
        uuid=this_id,
        creation_time=request.request_time,
        file_location=path,
        data=modules
    )


@router.get("/list", response_model=StaticItems)
def get_all_static_items():
    # Retrieve static locations
    logger.info("Retrieving static items")

    items = {"request_time": str(time.time())}
    if not os.path.exists(STATIC_PATH):
        logger.warning(f"No folder for static items exists at {STATIC_PATH}")
        return items

    if len(os.listdir(STATIC_PATH)) == 0:
        logger.warning(f"No static items found at {STATIC_PATH}")
        return items

    items["items"] = {}
    for file in os.listdir(STATIC_PATH):
        if os.path.splitext(file)[-1] != ".json":
            continue
        try:
            path = os.path.join(STATIC_PATH, file)
            with open(path, "r") as f:
                item = json.load(f)
            response_item = StaticItemResponse(
                name=item["name"],
                data=item["data"]
            )  
            items["items"][item["uuid"]] = response_item
        except Exception as e:
            raise e

    return items
            
