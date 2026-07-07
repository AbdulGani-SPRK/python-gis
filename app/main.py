from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import ErrorHandlingMiddleware, RequestIDMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level)
    logger.info("starting_service", extra={"service": settings.app_name, "env": settings.environment})
    yield
    logger.info("stopping_service", extra={"service": settings.app_name})


def create_app() -> FastAPI:
    tags_metadata = [
        {
            "name": "properties",
            "description": "Operations with properties. Includes spatial search and ranking based on OpenStreetMap amenities.",
        }
    ]

    app = FastAPI(
        title=settings.app_name,
        description="A GIS-enabled Property Consultant API supporting spatial queries, place resolution, and custom ranking.",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        openapi_tags=tags_metadata,
        contact={
            "name": "Property Consultant Support",
            "email": "support@propertyconsultant.example.com",
        },
    )
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()

