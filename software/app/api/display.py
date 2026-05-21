import json
import time
import logging
from datetime import datetime
from typing import List

from dataclasses import asdict
from fastapi import APIRouter, Depends, Request, status, HTTPException
from fastapi.responses import JSONResponse

from app.api.dependencies import get_display
from app.api.models.responses import DisplayResponse
import app.api.models.requests as reqs
from control.source.dataclasses_ import IncomingMessage
from control.source.flaps import Flap
from control.source.module_controller import ModuleController
from utils import get_current_timestamp, TIMESTAMP_FORMAT

router = APIRouter(
    prefix="/display",
    tags=["Display Control"]
)

logger = logging.getLogger("DisplayAPI")

def package_display_response(display_response: List[IncomingMessage]) -> DisplayResponse:
    output = {
        "request_time": get_current_timestamp(),
        "data": []
    }
    for data in display_response:
        json_data = asdict(data)
        json_data["location"] = data.location_map
        json_data["latency_ms"] = asdict(data.latency_ms)
        output["data"].append(json_data)
    return DisplayResponse(**output)

def exception_response(e: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error while communicating with display. Error: {str(e)}"
    )

@router.get("/steps", response_model=DisplayResponse)
def get_module_steps(display = Depends(get_display)):  
    try:
        response = display.get_all_steps()
    except Exception as e:
        raise exception_response(e)
    return package_display_response(response)

@router.get("/positions/{position}", response_model=DisplayResponse)
def get_position_steps(position: int, display = Depends(get_display)) -> Dict[str, str]:
    try:       
        response = display.get_position_steps(position)
    except Exception as e:
        raise exception_response(e)
    return package_display_response(response)
    
@router.post("/positions/{position}", response_model=DisplayResponse)
def move_all_to_position(position: int, display = Depends(get_display)) -> Dict[str, str]:
    try:
        response = display.move_all_to_position(position)
    except Exception as e:
        raise exception_response(e)
    return package_display_response(response)

@router.post("/positions", response_model=DisplayResponse)
def move_to_positions(positions: reqs.DisplayPositionRequest, display = Depends(get_display)):
    request_data = {}
    for request in positions.module_requests:
        if not ModuleController.is_valid_position(request.position):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Position value '{position}' is not valid"
            )
        request_data[request.location.as_tuple()] = request.position
    
    try:
        response = display.move_to_position(request_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while trying to move to position: {str(e)}"
        )
    return package_display_response(response)

@router.post("/flaps", response_model=DisplayResponse)
def move_to_flaps(flaps: reqs.DisplayFlapRequest, display = Depends(get_display)):
    request_data = {}
    for request in flaps.module_requests:
        try:
            flap = Flap[request.flap.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Flap value '{request.flap}' is not valid"
            )
        request_data[request.location.as_tuple()] = flap
    
    try:
        response = display.move_to_flaps(request_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while trying to move to flap: {str(e)}"
        )
    return package_display_response(response)