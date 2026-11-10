import logging

from .dependencies import get_playlist, get_app_loader, get_database

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from app.api.models.playlist import (
    ActiveItemResponse,
    AddItemRequest,
    ItemResponse,
    PlaylistResponse,
    FrequencyResponse,
    StatusResponse
)
from app.components.core.app_loader import AppNotAvailable


router = APIRouter(prefix="/playlist", tags=["Playlist"])
logger = logging.getLogger("DisplayAPI")

def create_status_response(playlist: DisplayPlaylist) -> StatusResponse:

    item = None
    if playlist.size > 0:
        item = ItemResponse(
            index=playlist.current_index,
            name=playlist.current_item.name,
            uuid=playlist.current_item.uuid,
            frequency=playlist.current_item.frequency.to_dict(),
            params=playlist.current_item.params,
        )

    time_data = None
    if playlist.is_alive:
        time_data = playlist.current_item.time_status.to_dict()

    return StatusResponse(
        is_active=playlist.is_alive,
        numItems=playlist.size,
        currentItem=item,
        currentItemTime=time_data
    )

@router.get("/status", response_model=StatusResponse)
def playlist_active(playlist=Depends(get_playlist)):
    # Respond with status
    return create_status_response(playlist)

@router.post("/start")
def start_playlist(playlist=Depends(get_playlist)):
    logger.info("Stopping playlist")
    try:
        playlist.start()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error occurred starting playlist: {str(e)}",
        )
    return create_active_item_response(playlist)

@router.post("/stop")
def stop_playlist(playlist=Depends(get_playlist)):
    logger.info("Stopping playlist")
    try:
        playlist.stop()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error occurred stopping playlist: {str(e)}",
        )
    return ItemResponse(
        index=0,
        name=playlist.current_item.name,
        uuid=playlist.current_item.uuid,
        frequency=playlist.current_item.frequency.to_dict(),
        params=playlist.current_item.params
    )
    
@router.get("/list", response_model=PlaylistResponse)
def get_current_playlist(playlist=Depends(get_playlist)):
    items = []
    for index, item in enumerate(playlist.items):
        this_item = ItemResponse(
            index=index,
            name=item.name,
            uuid=item.uuid,
            frequency=item.frequency.to_dict(),
            params=item.params
        )
        items.append(this_item)
    
    return PlaylistResponse(
        is_active=playlist.is_alive,
        current_index=playlist.current_index,
        frequency=playlist.frequency.to_dict(),
        items=items
    )

@router.post("/add")
def add_playlist_item(request: AddItemRequest, database=Depends(get_database), apps=Depends(get_app_loader), playlist=Depends(get_playlist)):
    try:
        app_info = apps.get(request.item_type)
    except AppNotAvailable as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App requested is not available - {str(exc)}",
        ) from exc

    app_class = app_info.obj
    if not isinstance(app_class, type):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"App '{request.item_type}' did not resolve to a class object",
        )
    
    if request.item_type == "StaticDisplayItem":
        assert "static_item_uuid" in request.parameters, "No UUID included in request"
        with database.connect() as db:
            item = db.get_item_from_uuid(request.parameters["static_item_uuid"])
            print(item)
    else:
        item = app_class(**request.parameters)
    playlist.add_item(item)
    return {"status": "ok", "item_type": request.item_type, "uuid": item.uuid}