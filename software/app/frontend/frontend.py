import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

logger = logging.getLogger("Frontend")
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    # Renders your simple HTML grid page instantly
    return templates.TemplateResponse("index.html", {"request": request})