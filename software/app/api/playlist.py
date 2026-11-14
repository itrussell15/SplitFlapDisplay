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

from app.api.models.static_items import StaticItem
from app.api.common import exception_response
from app.components.core.app_loader import AppNotAvailable
from app.components.core.playlist import PlaylistItem


router = APIRouter(prefix="/playlist", tags=["Playlist"])
logger = logging.getLogger("DisplayAPI")

def item_response(index: int, item: PlaylistItem) -> ItemResponse:
    return ItemResponse(
            index=index,
            name=item.name,
            uuid=item.uuid,
            frequency=item.frequency.to_dict() if item.frequency else None,
            params=item.params,
        )

def create_status_response(playlist: DisplayPlaylist) -> StatusResponse:

    item = None
    if playlist.size > 0:
        item = item_response(
            index=playlist.current_index,
            item=playlist.current_item
        )

    item_time_data = None
    playlist_time_data = None
    if playlist.is_alive:
        if playlist.current_item.is_dynamic:
            item_time_data = playlist.current_item.time_status.to_dict()
        playlist_time_data = playlist.time_status.to_dict() if playlist.time_status else None

    return StatusResponse(
        is_active=playlist.is_alive,
        numItems=playlist.size,
        playlistFrequency=playlist.frequency.to_dict(),
        currentItem=item,
        currentItemTime=item_time_data,
        playlistTime=playlist_time_data
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
    return item_response(
            index=playlist.current_index,
            item=playlist.current_item
        )

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
    return item_response(index=playlist.current_index, item=playlist.current_item)
    
@router.get("/list", response_model=PlaylistResponse)
def get_current_playlist(playlist=Depends(get_playlist)):
    items = []
    for index, item in enumerate(playlist.items):
        this_item = item_response(
            index=index,
            item=item
        )
        items.append(this_item)
    
    return PlaylistResponse(
        is_active=playlist.is_alive,
        current_index=playlist.current_index,
        frequency=playlist.frequency.to_dict(),
        items=items
    )

@router.post("/add")
def add_playlist_item(
    request: AddItemRequest,
    database=Depends(get_database),
    apps=Depends(get_app_loader),
    playlist=Depends(get_playlist)
):

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
        if "static_item_uuid" not in request.parameters:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"No uuid provided for static display item",
            )
        with database.connect() as db:
            item = db.get_item_from_uuid(request.parameters["static_item_uuid"]).to_static_display_item()
    else:
        item = app_class(**request.parameters)
    playlist.add_item(item)
    return {"status": "ok", "item_type": request.item_type, "uuid": item.uuid}