from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.logging import get_logger

logger = get_logger(__name__)


class RadSightException(Exception):
    def __init__(self, message: str, status_code: int = 500, detail: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


class NotFoundError(RadSightException):
    def __init__(self, resource: str, identifier: str = ""):
        super().__init__(f"{resource} not found", status_code=404, detail={"resource": resource, "id": identifier})


class UnauthorizedError(RadSightException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class ForbiddenError(RadSightException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403)


class ConflictError(RadSightException):
    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class ProcessingError(RadSightException):
    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message, status_code=422, detail=detail or {})


async def radsight_exception_handler(request: Request, exc: RadSightException) -> JSONResponse:
    logger.warning("RadSight exception", path=request.url.path, status=exc.status_code, msg=exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.message, "detail": exc.detail},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    logger.warning("HTTP exception", path=request.url.path, status=exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail, "detail": {}},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [{"field": ".".join(str(l) for l in e["loc"]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "message": "Validation failed", "detail": {"errors": errors}},
    )
