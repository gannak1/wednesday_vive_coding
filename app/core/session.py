import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        session_id = request.cookies.get(settings.session_cookie_name)

        if not _is_valid_uuid(session_id):
            session_id = str(uuid.uuid4())

        request.state.session_id = session_id
        response = await call_next(request)
        response.set_cookie(
            key=settings.session_cookie_name,
            value=session_id,
            max_age=settings.session_cookie_max_age,
            httponly=True,
            samesite="lax",
            secure=settings.session_cookie_secure,
            path="/",
        )
        return response


def _is_valid_uuid(value: str | None) -> bool:
    if not value:
        return False
    try:
        uuid.UUID(str(value))
    except ValueError:
        return False
    return True
