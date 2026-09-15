from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from tenacity import RetryError

from app.api import routes_artifacts, routes_chat, routes_health, routes_sessions
from app.config import get_settings
from app.core.exceptions import AppError
from app.logging_config import configure_logging, get_logger

configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("app_starting", env=get_settings().app_env)
    yield
    log.info("app_shutdown")


app = FastAPI(
    title="Lenny Growth Assistant API",
    version="1.0.0",
    description="Grounded conversational assistant over Lenny's Podcast transcripts.",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    log.error("app_error", code=exc.code, detail=exc.detail, path=str(request.url))
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.code, "detail": exc.detail, "code": exc.code},
    )


@app.exception_handler(RetryError)
async def retry_error_handler(request: Request, exc: RetryError) -> JSONResponse:
    inner = exc.last_attempt.exception()
    if isinstance(inner, AppError):
        return await app_error_handler(request, inner)
    log.error("unhandled_retry_error", error=str(inner), path=str(request.url))
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": str(inner), "code": "internal_error"},
    )

@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    import traceback

    tb = traceback.format_exc()
    log.error("unhandled_error", error=str(exc), path=str(request.url), traceback=tb)

    detail = "An unexpected error occurred."
    if settings.app_env != "production":
        detail = f"{exc.__class__.__name__}: {exc}"

    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": detail, "code": "internal_error"},
    )


app.include_router(routes_health.router)
app.include_router(routes_sessions.router)
app.include_router(routes_chat.router)
app.include_router(routes_artifacts.router)
