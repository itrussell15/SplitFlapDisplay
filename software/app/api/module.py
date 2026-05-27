import logging


from fastapi import APIRouter, Depends, HTTPException, Request, status

from .dependencies import get_display
from .common import exception_response, package_incoming_message_as_module_response
from control.source.flaps import Flap
from app.api.models.common import Location 
from app.api.models.responses import ModuleResponse, PositionResponse
from app.api.models.requests import StepRequest, FlapRequest, PositionRequest, LocationRequest
from utils import get_current_timestamp, TIMESTAMP_FORMAT

router = APIRouter(prefix="/modules", tags=["Module Control"])
logger = logging.getLogger("DisplayAPI")

@router.get("/steps", response_model=ModuleResponse)
def get_module_steps(location: Location, display=Depends(get_display)):
    try:
        response = display.get_module(*location.as_tuple()).get_steps()
    except Exception as e:
        raise exception_response(e)
    return package_incoming_message_as_module_response(response)

@router.post("/steps/{steps}", response_model=ModuleResponse)
def move_to_module_steps(steps: int, location: Location, display=Depends(get_display)):
    try:
        response = display.get_module(*location.as_tuple()).move_to_step(steps)
    except Exception as e:
        raise exception_response(e)
    return package_incoming_message_as_module_response(response)

@router.post("/flap", response_model=ModuleResponse)
def move_to_flap(request: FlapRequest, display=Depends(get_display)):
    try:
        flap = Flap[request.flap.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid flap input - {request.flap}",
        )

    try:
        response = display.get_module(*request.location.as_tuple()).move_to_position(flap.value)
    except Exception as e:
        raise exception_response(e)
    return package_incoming_message_as_module_response(response)

@router.get("/position", response_model=PositionResponse)
def get_all_positions(request: LocationRequest, display=Depends(get_display)):
    try:
        response = display.get_module(*request.location.as_tuple()).get_all_positions()
    except Exception as e:
        raise exception_response(e)
    
    output = {"request_time": get_current_timestamp(), "positions": response}
    return output

@router.post("/position", response_model=ModuleResponse)
def move_to_position(request: PositionRequest, display=Depends(get_display)):
    print(request)
    try:
        response = display.get_module(*request.location.as_tuple()).move_to_position(request.position)
    except Exception as e:
        raise exception_response(e)
    return package_incoming_message_as_module_response(response)

@router.post("/home", response_model=ModuleResponse)
def home_module(location: Location, display=Depends(get_display)):
    try:
        response = display.get_module(*location.as_tuple()).home()
    except Exception as e:
        raise exception_response(e)
    return package_incoming_message_as_module_response(response)

@router.get("/position/{position}", response_model=ModuleResponse)
def get_module_position(position: int, location: Location, display=Depends(get_display)):
    try:
        response = display.get_module(*location.as_tuple()).get_position(position)
    except Exception as e:
        raise exception_response(e)
    return package_incoming_message_as_module_response(response)

# This is on hold as the current firmware requires you to move to the position to save it 
# @router.post("/position/{position}")
# def get_module_position(position: int, steps_request: StepRequest, display=Depends(get_display)):
#     try:
#         response = display.get_module(*steps_request.location.as_tuple()).set_position(position)
#     except Exception as e:
#         raise exception_response(e)
#     return package_incoming_message_as_module_response(response)

