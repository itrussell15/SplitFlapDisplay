import json
import logging
import time
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Tuple

import app.api.common as common
from app.api.dependencies import get_database
from app.api.models.flaps import Flaps, FlapData, FlapUpdateRequest
from fastapi import APIRouter, Depends, HTTPException, Request, status
from utils import get_current_timestamp, TIMESTAMP_FORMAT

from .common import exception_response

router = APIRouter(prefix="/flaps", tags=["Flaps"])
logger = logging.getLogger("DisplayAPI")

@router.get("/valid")
def are_flaps_valid(database=Depends(get_database)):
    return {"valiid": database.flap_positions_initialized()}

@router.get("/", response_model=Flaps)
def get_flaps(database=Depends(get_database)):
    if not database.flap_positions_initialized():
        exception_response("Flap posiitons not initialized")
    with database.connect() as db:
        flaps = db.get_flaps()
    return flaps

@router.get("/position")
def get_flap_characters_by_position(database=Depends(get_database)):
    if not database.flap_positions_initialized():
        exception_response("Flap posiitons not initialized")
    with database.connect() as db:
        chars = db.get_all_flap_characters_by_position()
    return chars

@router.get("/position/{position}")
def get_flap_data_by_position(position: int, database=Depends(get_database)):
    if not database.flap_positions_initialized():
        exception_response("Flap posiitons not initialized")
    with database.connect() as db:
        flap_data = db.get_flap_data_by_position(position)
    return flap_data

@router.get("/character")
def get_flap_position_by_character(database=Depends(get_database)):
    if not database.flap_positions_initialized():
        exception_response("Flap posiitons not initialized")
    with database.connect() as db:
        chars = db.get_all_flap_position_by_character()
    return chars

@router.get("/character/{character}")
def get_flap_data_by_position(character: str, database=Depends(get_database)):
    if not database.flap_positions_initialized():
        exception_response("Flap posiitons not initialized")
    with database.connect() as db:
        flap_data = db.get_flap_data_by_character(character)
    return flap_data

@router.post("/", response_model=FlapData)
def add_flap(request: FlapData, database=Depends(get_database)):
    logger.info(f"Request received to add {(request.key, request.glyph)} at position {request.position}")
    with database.connect() as db:
        row = db.add_flap(request.position, request.key, request.glyph, request.color_hex)
    return row

@router.put("/")
def update_flap(request: FlapUpdateRequest, database=Depends(get_database)):
    if not database.flap_positions_initialized():
        exception_response("Flap posiitons not initialized")
    logger.info(f"Request received to update flap {request.position} to {(request.key, request.glyph)}")
    with database.connect() as db:
        db.update_flap(
            position=request.position,
            flap_data=FlapData(
                position=request.position,
                key=request.key,
                glyph=request.glyph,
                color_hex=request.color_hex,
            ),
        )
