import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.config import Settings

logger = logging.getLogger(__name__)


def _apply_cors(response: JSONResponse, request: Request, settings: Settings) -> JSONResponse:
    """Mirrors CORSMiddleware's own decision for this request's Origin.

    A response built and returned directly from one of these handlers isn't
    reliably decorated with CORS headers by the outer CORSMiddleware --
    Starlette's ExceptionMiddleware (which invokes these) sits at a
    different point in the stack for a registered HTTPException handler
    than it does for a still-unhandled Exception, and a cross-origin
    response with no Access-Control-Allow-Origin header is a hard network
    failure to the browser (no status, no body ever reach the page's JS),
    not a readable error. A real 500 elsewhere in the app looked to the
    frontend exactly like the backend was unreachable (found via a live
    user report: deleting a Timetable block returned a clean 500 body via
    curl, but the browser only ever surfaced "Failed to fetch").
    """
    origin = request.headers.get("origin")
    allowed = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]
    if origin and origin in allowed:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response


def register_exception_handlers(app: FastAPI, settings: Settings) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        response = JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "request_id": getattr(request.state, "request_id", None),
            },
            headers=exc.headers,
        )
        return _apply_cors(response, request, settings)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        response = JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": exc.errors(),
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return _apply_cors(response, request, settings)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            extra={"path": request.url.path, "method": request.method},
            exc_info=exc,
        )
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return response
