import logging

from .dependencies import get_playlist

from fastapi import APIRouter, Depends, HTTPException, Request, status



router = APIRouter(prefix="/playlist", tags=["Playlist"])
logger = logging.getLogger("DisplayAPI")

@router.get("/list")
def get_current_playlist(playlist=Depends(get_playlist)):
    print(playlist.items)
