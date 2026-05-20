import logging
from fastapi import APIRouter, Request, status

router = APIRouter(
    prefix="/display",
    tags=["Display Control"]
)

logger = logging.getLogger("DisplayAPI")

@router.post("/clear", status_code=status.HTTP_200_OK)
def clear_display(request: Request) -> Dict[str, str]:
    return {"status": "OK"}