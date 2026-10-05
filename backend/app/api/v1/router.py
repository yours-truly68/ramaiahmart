from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.categories import router as categories_router
from app.api.v1.legal import router as legal_router
from app.api.v1.media import router as media_router
from app.api.v1.posts import router as posts_router
from app.api.v1.users import router as users_router

router = APIRouter()


# Health check
@router.get("/health", summary="Service Health Check")
def health_check() -> dict[str, str]:
    """Return health status of the application."""
    return {"status": "ok"}


# Domain sub-routers
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(categories_router)
router.include_router(posts_router)
router.include_router(media_router)
router.include_router(legal_router)
