from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class AppInfoResponse(BaseModel):
    name: str
    app_image: str | None
    description: str | None
    parameters: Dict[str, Any] | None
    file_path: str

class AvailableAppsResponse(BaseModel):
    num_apps: int
    source_paths: List[str]
    apps: List[AppInfoResponse]