from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.category import Category
from app.schemas.category import CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get(
    "",
    response_model=list[CategoryResponse],
    summary="List active categories",
)
def list_categories(
    db: Session = Depends(get_db),
) -> list[CategoryResponse]:
    """Retrieve all active marketplace categories ordered by name."""
    stmt = select(Category).where(Category.is_active.is_(True)).order_by(Category.name.asc())
    categories = db.scalars(stmt).all()
    return [CategoryResponse.model_validate(cat) for cat in categories]
