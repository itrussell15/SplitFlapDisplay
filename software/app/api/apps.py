import json
import logging
import time
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Tuple

import app.api.common as common
import app.api.models.requests as reqs
import app.api.models.responses as resps
from app.api.dependencies import get_app_loader
from app.api.models.apps import AvailableAppsResponse
from app.components.display_playlist.display_item import DisplayItem, DisplayItemType, StaticDisplayItem

from fastapi import APIRouter, Depends, HTTPException, Request, status
from utils import get_current_timestamp, TIMESTAMP_FORMAT

from .common import exception_response, package_incoming_message_as_module_response

router = APIRouter(prefix="/apps", tags=["Integrations", "Apps"])
logger = logging.getLogger("AppsAPIS")

@router.get("/list", response_model=AvailableAppsResponse)
def list_available_apps(apps=Depends(get_app_loader)):

    def output_format(app_info: AppInfo) -> Dict[str, str]:
        return {
            "name": app_info.name,
            "description": app_info.description,
            "app_image": app_info.app_image,
            "parameters": app_info.parameters,
            "file_path": app_info.file_path
        }

    return {
        "num_apps": len(apps),
        "source_paths": set(apps.sources),
        "apps": [output_format(app) for app in apps.get_all_apps().values()]
    }