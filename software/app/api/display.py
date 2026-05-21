import json
import time
import logging
from typing import List

from dataclasses import asdict
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.api.dependencies import get_display
from app.api.responses import DisplayResponse
from control.source.dataclasses_ import IncomingMessage
from utils import get_current_timestamp

router = APIRouter(
    prefix="/display",
    tags=["Display Control"]
)

logger = logging.getLogger("DisplayAPI")

def package_display_response(display_response: Dict[Tuple[int, int], IncomingMessage]) -> DisplayResponse:
    output = {
        "request_time": get_current_timestamp(),
        "data": []
    }
    for location, data in display_response.items():
        json_data = asdict(data)
        json_data["location"] = data.location_map
        json_data["times"] = asdict(data.times)
        output["data"].append(json_data)
    return DisplayResponse(**output)

@router.get("/steps", response_model=DisplayResponse)
def get_module_steps(display = Depends(get_display)):   
    try:
        response = display.get_all_steps()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting steps from display. Error: {str(e)}"
        )
    return package_display_response(response)

@router.get("/positions/{position}", response_model=DisplayResponse)
def get_position_steps(position: int, display = Depends(get_display)) -> Dict[str, str]:
    response = display.get_position_steps(position)
    output = {
        "request_time": get_current_timestamp(),
        "data": []
    }
    for location, data in response.items():
        json_data = asdict(data)
        json_data["location"] = data.location_map
        output["data"].append(json_data)
    return package_display_response(response)
    
@router.post("/positions/{position}")
def move_all_to_position(position: int, display = Depends(get_display)) -> Dict[str, str]:
    response = display.move_all_to_position(position)
    output = {
        "request_time": get_current_timestamp(),
        "data": []
    }
    for location, data in response.items():
        output["data"].append(asdict(data))
    result = json.dumps(output)
    return JSONResponse(result)
