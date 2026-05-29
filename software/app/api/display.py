import json
import logging
import time
from dataclasses import asdict
from datetime import datetime
from typing import Dict, List, Tuple

import app.api.common as common
import app.api.models.requests as reqs
from app.api.dependencies import get_display
from app.api.models.responses import DiscoverResponse, DisplayResponse
from control.source.dataclasses_ import IncomingMessage
from control.source.flaps import Flap
from control.source.module_controller import ModuleController
from fastapi import APIRouter, Depends, HTTPException, Request, status
from utils import get_current_timestamp, TIMESTAMP_FORMAT

from .common import exception_response, package_incoming_message_as_module_response

router = APIRouter(prefix="/display", tags=["Display Control"])
logger = logging.getLogger("DisplayAPI")


def package_display_response(
    display_response: List[IncomingMessage],
) -> DisplayResponse:
    output = {"request_time": get_current_timestamp(), "data": []}
    for message in display_response:
        # Package incoming message
        output["data"].append(package_incoming_message_as_module_response(message))
    return DisplayResponse(**output)


def package_location(location: Tuple[int, int]) -> Dict[int, int]:
    return {
        "row": location[0],
        "column": location[1],
    }


@router.get("/info")
def get_display_info(display=Depends(get_display)):
    rows, columns = display.get_rows_and_columns()
    return {
        "num_modules": display.num_modules,
        "num_buses": display.num_buses,
        "rows": rows,
        "columns": columns,
    }


@router.post("/discover", response_model=DiscoverResponse)
def discover(display=Depends(get_display)):
    try:
        response = display.discover([0, 2], [0, 2])
    except Exception as e:
        raise exception_response(e)

    locations = []
    for location in response:
        locations.append(package_location(location))
    return {
        "request_time": get_current_timestamp(),
        "num_modules": display.num_modules,
        "num_buses": display.num_buses,
        "locations": locations,
    }


@router.get("/steps", response_model=DisplayResponse)
def get_module_steps(display=Depends(get_display)):
    try:
        response = display.get_all_steps()
    except Exception as e:
        raise exception_response(e)
    return package_display_response(response)


@router.get("/positions/{position}", response_model=DisplayResponse)
def get_position_steps(position: int, display=Depends(get_display)) -> Dict[str, str]:
    try:
        response = display.get_position_steps(position)
    except Exception as e:
        raise exception_response(e)
    return package_display_response(response)


@router.post("/positions/{position}", response_model=DisplayResponse)
def move_all_to_position(position: int, display=Depends(get_display)) -> Dict[str, str]:
    try:
        response = display.move_all_to_position(position)
    except Exception as e:
        raise common.exception_response(e)
    return package_display_response(response)


@router.get("/positions")
def get_position_steps(display=Depends(get_display)) -> Dict[str, str]:
    try:
        response = display.get_current_positions()
    except Exception as e:
        raise exception_response(e)
    return package_display_response(response)


@router.post("/positions", response_model=DisplayResponse)
def move_to_positions(
    positions: reqs.DisplayPositionRequest, display=Depends(get_display)
):
    request_data = {}
    for request in positions.module_requests:
        if not ModuleController.is_valid_position(request.position):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Position value '{request.position}' is not valid",
            )
        request_data[request.location.as_tuple()] = request.position

    try:
        response = display.move_to_position(request_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while trying to move to position: {str(e)}",
        )
    return package_display_response(response)


@router.get("/flap")
def get_flaps():
    return {flap.name: flap.value for flap in Flap}


@router.post("/flap", response_model=DisplayResponse)
def move_to_flaps(flaps: reqs.DisplayFlapRequest, display=Depends(get_display)):
    request_data = {}
    for request in flaps.module_requests:
        try:
            flap = Flap[request.flap.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Flap value '{request.flap}' is not valid",
            )
        request_data[request.location.as_tuple()] = flap

    try:
        response = display.move_to_flaps(request_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while trying to move to flap: {str(e)}",
        )
    return package_display_response(response)


@router.post("/home", response_model=DisplayResponse)
def home_all(display=Depends(get_display)):
    try:
        response = display.home_all()
    except Exception as e:
        raise common.exception_response(e)
    return package_display_response(response)
