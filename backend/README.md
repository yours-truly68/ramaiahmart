# RamaiahMart Backend

FastAPI backend service for RamaiahMart, a university-only marketplace for Ramaiah students.

## Architecture & Tech Stack

- **Python 3.13**
- **FastAPI** — high performance web framework
- **Pydantic v2 & pydantic-settings** — typed configuration & schema validation
- **SQLAlchemy 2.x** — modern SQL ORM with declarative mapping
- **Alembic** — database schema migrations
- **PostgreSQL & psycopg 3** — persistent relational storage
- **uv** — fast Python package manager
- **Ruff** — fast linter & code formatter
- **pytest & pytest-asyncio & httpx** — testing suite
- **Docker & Docker Compose** — containerized local and production execution

---

## Local Development with Docker Compose

Start the full stack (PostgreSQL + FastAPI):

```bash
docker compose up --build
```

Once running, access the services:

- **API Base**: [http://localhost:8000](http://localhost:8000)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Stopping the Stack

To stop containers:

```bash
docker compose down
```

To stop containers and remove persistent database volumes:

```bash
docker compose down -v
```

---

## Local Development without Docker

### 1. Install Dependencies

Using `uv`:

```bash
uv sync
```

### 2. Environment Variables

Copy the sample environment file:

```bash
cp .env.example .env
```

### 3. Run the Development Server

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Testing

Run the test suite:

```bash
uv run pytest
```

---

## Code Quality & Formatting

Run lint checks:

```bash
uv run ruff check .
```

Auto-fix lint errors:

```bash
uv run ruff check --fix .
```

Check code formatting:

```bash
uv run ruff format --check .
```

Format code:

```bash
uv run ruff format .
```

---

## Database Migrations

Generate a new migration after updating models:

```bash
uv run alembic revision --autogenerate -m "describe_migration"
```

Apply pending migrations:

```bash
uv run alembic upgrade head
```

Rollback the last migration:

```bash
uv run alembic downgrade -1
```
