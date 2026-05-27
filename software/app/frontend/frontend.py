import os
import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(include_in_schema=False)

logger = logging.getLogger("Frontend")
template_path = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=template_path)


@router.get("/")
async def read_index(request: Request):
    # Renders your simple HTML grid page instantly
    return templates.TemplateResponse(request, "index.html")