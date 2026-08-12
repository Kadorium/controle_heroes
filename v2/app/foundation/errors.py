from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "app_error",
        status_code: int = 400,
        details: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    body: dict = {"error": exc.code, "message": exc.message}
    if exc.details:
        body["details"] = exc.details
    return JSONResponse(
        status_code=exc.status_code,
        content=body,
    )


async def http_error_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "http_error", "message": detail},
    )
