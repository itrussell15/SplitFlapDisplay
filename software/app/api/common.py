from dataclasses import asdict
from typing import Any, Dict

from app.api.models.responses import ModuleResponse
from control.source.dataclasses_ import IncomingMessage
from fastapi import HTTPException, status


def exception_response(e: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error while communicating with display. Error: {str(e)}",
    )


def package_incoming_message_as_module_response(
    message: IncomingMessage,
) -> Dict[str, Any]:
    json_data = asdict(message)
    json_data["location"] = message.location_map
    json_data["latency_ms"] = asdict(message.latency_ms)
    return json_data
