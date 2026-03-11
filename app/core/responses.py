from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(message: str, data: Any, status_code: int = 200) -> JSONResponse:
    payload = {
        "success": True,
        "message": message,
        "data": jsonable_encoder(data),
    }
    return JSONResponse(status_code=status_code, content=payload)


def error_response(status_code: int, message: str, error_code: str) -> JSONResponse:
    payload = {
        "success": False,
        "message": message,
        "error_code": error_code,
    }
    return JSONResponse(status_code=status_code, content=payload)
