"""Add the initial marketplace taxonomy without modifying existing categories/posts.

Run from backend: .venv/bin/python -m scripts.seed_categories
"""

from sqlalchemy.dialects.postgresql import insert

from app.db.session import SessionLocal
from app.models.category import Category

CATEGORIES = [
    ("Electronics", "electronics"),
    ("Books", "books"),
    ("Furniture", "furniture"),
    ("Vehicles", "vehicles"),
    ("Housing", "housing"),
    ("Notes", "notes"),
    ("Fashion", "fashion"),
    ("Sports", "sports"),
    ("Other", "other"),
]

if __name__ == "__main__":
    with SessionLocal.begin() as session:
        for name, slug in CATEGORIES:
            session.execute(
                insert(Category)
                .values(name=name, slug=slug, is_active=True)
                .on_conflict_do_nothing(index_elements=["slug"])
            )
    print("Initial marketplace categories are available.")
