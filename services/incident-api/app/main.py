from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health, incidents
from app.config import get_settings
from app.errors import AppError
from app.logging import configure_logging
from app.middleware.errors import (
    app_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from app.middleware.request_context import request_context_middleware
from app.registry import get_services

settings = get_settings()
configure_logging(settings)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    services = get_services()
    yield
    await services.database.close()


app = FastAPI(
    title="Incident Analysis API",
    version="0.1.0",
    description="Read-only, human-in-the-loop incident evidence analysis.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["content-type", "x-request-id"],
)
app.middleware("http")(request_context_middleware)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unexpected_error_handler)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(incidents.router)
