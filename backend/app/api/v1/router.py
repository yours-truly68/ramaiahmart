from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Service Health Check")
def health_check() -> dict[str, str]:
    """Return health status of the application."""
    return {"status": "ok"}
