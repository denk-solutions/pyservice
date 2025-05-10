from fastapi import FastAPI, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, NoResultFound

import pyservice.logger as logger
from pyservice.api.routers.auth import router as auth_router
from pyservice.exc import AuthError
from pyservice.version import __version__


async def integrity_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Capture database integrity errors."""
    logger.error("Encountered exception in request:", exc_info=True)
    return JSONResponse(
        content={
            "detail": (
                "Data integrity conflict. This usually means a "
                "unique or foreign key constraint was violated. "
                "See server logs for details."
            )
        },
        status_code=status.HTTP_409_CONFLICT,
    )


async def no_result_found_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Capture database result not found errors."""
    logger.error("Encountered exception in request:", exc_info=True)
    return JSONResponse(
        content={"detail": "Object not found"},
        status_code=status.HTTP_404_NOT_FOUND,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Provide a detailed message for request validation errors."""
    logger.debug("Encountered exception in request:", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {
                "exception_message": "Invalid request received.",
                "exception_detail": exc.errors(),
                "request_body": exc.body,
            }
        ),
    )


async def auth_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Encountered exception in request:", exc_info=True)
    return JSONResponse(
        content={"detail": "Not authenticated"},
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


async def internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Log a detailed exception for internal server errors before returning.
    """
    logger.error("Encountered exception in request:", exc_info=True)
    return JSONResponse(
        content={"exception_message": "Internal Server Error"},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


app = FastAPI(
    title="pyservice",
    version=__version__,
    exception_handlers={
        IntegrityError: integrity_exception_handler,
        RequestValidationError: validation_exception_handler,
        Exception: internal_exception_handler,
        NoResultFound: no_result_found_exception_handler,
        AuthError: auth_exception_handler,
    },
)
app.include_router(auth_router)
