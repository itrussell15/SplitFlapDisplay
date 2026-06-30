import os
import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(include_in_schema=False)

logger = logging.getLogger("Frontend")
template_path = os.path.join(os.path.dirname(__file__), "templates")
static_path = os.path.join(os.path.dirname(__file__), "static")
templates = Jinja2Templates(directory=template_path)


def _static_version() -> int:
    """Latest mtime across static assets, used to cache-bust /static URLs so a
    browser never serves a stale .js/.css after an edit."""
    latest = 0
    for root, _dirs, files in os.walk(static_path):
        for name in files:
            try:
                latest = max(latest, int(os.path.getmtime(os.path.join(root, name))))
            except OSError:
                pass
    return latest


def _render(request: Request, template: str, active: str, status_managed: bool = False):
    """Render a page that extends base.html.

    `active` highlights the matching sidebar item. `status_managed` tells
    base.js to leave the status text alone (the page's own JS owns it).
    """
    return templates.TemplateResponse(
        request,
        template,
        {
            "active": active,
            "status_managed": status_managed,
            "static_version": _static_version(),
        },
    )


@router.get("/")
async def read_index(request: Request):
    # Compose/display page — app.js manages the status text, so status_managed=True
    return _render(request, "index.html", active="display", status_managed=True)


@router.get("/apps")
async def read_apps(request: Request):
    return _render(request, "apps.html", active="apps")


@router.get("/tuning")
async def read_tuning(request: Request):
    return _render(request, "tuning.html", active="tuning")


@router.get("/settings")
async def read_settings(request: Request):
    return _render(request, "settings.html", active="settings")
