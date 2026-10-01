import logging

from .dependencies import get_playlist, get_app_loader

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from app.api.models.playlist import (
    AddItemRequest, ItemResponse, PlaylistResponse, FrequencyResponse
)
from app.components.core.app_loader import AppNotAvailable


router = APIRouter(prefix="/playlist", tags=["Playlist"])
logger = logging.getLogger("DisplayAPI")

@router.get("/status")
def playlist_active(playlist=Depends(get_playlist)):
    return {"is_active": playlist.is_alive} 

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
def add_playlist_item(request: AddItemRequest, apps=Depends(get_app_loader), playlist=Depends(get_playlist)):
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

    item = app_class(**request.parameters)
    playlist.add_item(item)
    return {"status": "ok", "item_type": request.item_type, "uuid": item.uuid}