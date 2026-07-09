import json
import logging
import time
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Tuple

import app.api.common as common
import app.api.models.requests as reqs
from app.api.models.common import Location
import app.api.dependencies as deps
import app.api.models.responses as resps
from app.components.rate_limiter import RateLimiter
from utils import get_current_timestamp, TIMESTAMP_FORMAT
from .common import exception_response

from fastapi import APIRouter, Depends, HTTPException, Request, status

router = APIRouter(prefix="/rate_limiting", tags=["Rate Limter"])
logger = logging.getLogger("RateLimterAPI")

class RateLimited(Exception):
    def __init__(self, target_time: datetime.datetime) -> None:
        super().__init__(f"Rate is limited until {target_time.strftime(TIMESTAMP_FORMAT)}")

def rate_response(rate_limiter: RateLimiter) -> RateResponse:
    rate = {
        "minutes": rate_limiter.rate.total_seconds() // 60,
        "seconds": rate_limiter.rate.seconds % 60
    }
    return {
        "rate": rate,
        "target_time": rate_limiter.target_time.strftime(TIMESTAMP_FORMAT) if rate_limiter.target_time is not None else None,
        "last_update": rate_limiter.last_update.strftime(TIMESTAMP_FORMAT) if rate_limiter.last_update is not None else None,
    }

@router.get("/rate", response_model=resps.RateResponse)
def get_rate_limiter(rate_limiter=Depends(deps.get_rate_limiter)) -> Dict[str, str]:
    return rate_response(rate_limiter)

@router.get("/check", response_model=resps.RateCheck)
def check_rate_limit(rate_limiter=Depends(deps.get_rate_limiter)) -> Dict[str, str]:
    try:
        state = rate_limiter.check()
        return {
            "status": state,
            "request_time": datetime.now().strftime(TIMESTAMP_FORMAT),
            "target_time": rate_limiter.target_time.strftime(TIMESTAMP_FORMAT) if rate_limiter.target_time is not None else None,
            "last_update": rate_limiter.last_update.strftime(TIMESTAMP_FORMAT) if rate_limiter.last_update is not None else None,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

@router.post("/rate", response_model=resps.RateResponse)
def set_rate_limiter(minutes: int, seconds: int, rate_limiter=Depends(deps.get_rate_limiter)) -> Dict[str, str]:
    rate_limiter.set_rate(minutes, seconds)
    return rate_response(rate_limiter)

@router.post("/update", response_model=resps.RateResponse)
def update_rate_limiter_time(rate_limiter=Depends(deps.get_rate_limiter)) -> Dict[str, str]:
    rate_limiter.update()
    return rate_response(rate_limiter)
    