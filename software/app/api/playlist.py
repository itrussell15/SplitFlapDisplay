import logging

from app.api.common import exception_response
from app.api.models.playlist import (
    ActiveEntryResponse,
    AddEntryRequest,
    AddItemRequest,
    EntryResponse,
    FrequencyModel,
    ItemResponse,
    PlaylistResponse,
    StatusResponse,
    TimeData,
)
from app.api.models.static_items import StaticItem
from app.components.core.app_loader import AppNotAvailable
from app.components.core.playlist import PlaylistEntry, PlaylistItem
from app.components.core.updater import UpdateFrequency
from app.components.display.playlist import DisplayPlaylist
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from .dependencies import get_app_loader, get_database, get_playlist


router = APIRouter(prefix="/playlist", tags=["Playlist"])
logger = logging.getLogger("DisplayAPI")


def item_response(item: PlaylistItem) -> ItemResponse:
    frequency = item.trigger.frequency if item.trigger is not None else None
    return ItemResponse(
        name=item.name,
        frequency=FrequencyModel(**frequency.to_dict()) if frequency else None,
        params=item.params,
    )


def entry_response(index: int, entry: PlaylistEntry) -> EntryResponse:
    item = item_response(entry.item)
    return EntryResponse(
        index=index,
        item=item,
        duration=FrequencyModel(**entry.duration.to_dict()),
        uuid=entry.uuid,
    )


def create_status_response(playlist: DisplayPlaylist) -> StatusResponse:
    entry = None
    if playlist.size > 0:
        entry = entry_response(
            index=playlist.current_index,
            entry=playlist.current_entry,
        )

    return StatusResponse(
        is_active=playlist.is_active,
        numItems=playlist.size,
        currentEntry=entry,
        currentEntryTime=(
            TimeData(**playlist.time_status.to_dict()) if playlist.time_status else None
        ),
    )


@router.get("/status", response_model=StatusResponse)
def playlist_active(playlist=Depends(get_playlist)):
    return create_status_response(playlist)


@router.post("/start", response_model=EntryResponse)
def start_playlist(playlist=Depends(get_playlist)):
    logger.info("Starting playlist")
    try:
        playlist.start()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error occurred starting playlist: {str(e)}",
        )
    return entry_response(index=playlist.current_index, entry=playlist.current_entry)


@router.post("/stop", response_model=EntryResponse)
def stop_playlist(playlist=Depends(get_playlist)):
    logger.info("Stopping playlist")
    try:
        playlist.stop()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error occurred stopping playlist: {str(e)}",
        )
    return entry_response(index=playlist.current_index, entry=playlist.current_entry)


@router.get("/playlist", response_model=PlaylistResponse)
def get_current_playlist(playlist=Depends(get_playlist)):
    entries = []
    for index, entry in enumerate(playlist.entries):
        this_item = entry_response(index=index, entry=entry)
        entries.append(this_item)

    return PlaylistResponse(
        is_active=playlist.is_active,
        current_index=playlist.current_index if not playlist.is_empty else None,
        current_entry=(
            entries[playlist.current_index] if not playlist.is_empty else None
        ),
        entries=entries,
    )


@router.post("/add")
def add_playlist_item(
    request: AddEntryRequest,
    database=Depends(get_database),
    apps=Depends(get_app_loader),
    playlist=Depends(get_playlist),
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
                detail="No uuid provided for static display item",
            )
        with database.connect() as db:
            item = db.get_item_from_uuid(
                request.parameters["static_item_uuid"]
            ).to_static_display_item()

    else:
        item = app_class(
            trigger_factory=app_class.trigger_factory,
            **request.parameters,
        )

    duration = request.duration.to_update_frequency()
    entry = playlist.add_entry(item=item, duration=duration)
    return {
        "status": "ok",
        "item_type": request.item_type,
        "uuid": entry.uuid,
        "duration": duration,
    }


@router.delete("/delete/{entry_uuid}")
def remove_playlist_entry(entry_uuid: str, playlist=Depends(get_playlist)):
    for index, entry in enumerate(playlist.entries):
        if entry.uuid == entry_uuid:
            break
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist entry not found",
        )

    logger.info("UUID found - deleteing item")
    try:
        playlist.remove_entry(index)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    return {"status": "ok", "uuid": entry_uuid}