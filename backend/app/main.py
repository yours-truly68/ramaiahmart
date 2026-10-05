from fastapi import FastAPI

from app.api.v1.router import router as api_v1_router
from app.core.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    application = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    application.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return application


app = create_app()
