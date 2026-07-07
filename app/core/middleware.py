import json
import logging
import time
import uuid
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id

        if logger.isEnabledFor(logging.DEBUG):
            request_json: Any | None = None
            try:
                body_bytes = await request.body()
                content_type = request.headers.get("content-type", "")
                if body_bytes and "application/json" in content_type.lower():
                    request_json = json.loads(body_bytes.decode("utf-8", errors="replace"))
            except Exception:
                request_json = None

            logger.debug(
                f"request_received id={request_id} method={request.method} path={request.url.path} body={json.dumps(request_json) if request_json else None}"
            )

        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["x-request-id"] = request_id
        logger.info(
            f"request_completed id={request_id} method={request.method} path={request.url.path} status={response.status_code} duration_ms={duration_ms}ms"
        )
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", None)
            logger.exception(
                "unhandled_error",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(exc).__name__,
                },
            )
            payload: dict[str, Any] = {
                "detail": "Internal server error",
                "request_id": request_id,
            }
            return JSONResponse(status_code=500, content=payload)

