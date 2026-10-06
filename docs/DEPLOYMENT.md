# RamaiahMart — Production Deployment & CI/CD Specification

## 1. Target Production Architecture

The production environment separates client delivery, public API routing, application compute, database persistence, and media storage into dedicated tiers:

```text
                         INTERNET
                            │
                            ▼
                    ┌──────────────┐
                    │    Vercel    │
                    │   Next.js    │
                    └──────────────┘

                         API TRAFFIC
                            │
                            ▼
                    ┌──────────────┐
                    │   AWS EC2    │
                    │              │
                    │    Nginx     │  (Port 80/443, SSL termination, rate-limiting)
                    │      │       │
                    │      ▼       │
                    │   FastAPI    │  (Port 8000, internal docker network only)
                    │              │
                    └──────┬───────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
                 AWS RDS        AWS S3
                PostgreSQL      Media
```

### Build & Release Pipeline

```text
GitHub Push / PR
       │
       ▼
GitHub Actions
 ├── CI: Lint, Typecheck, Test, Build, Docker Image Validation
 └── CD:
      ├── Build immutable image: ghcr.io/<owner>/ramaiahmart-api:<commit-sha>
      ├── Push to GitHub Container Registry (GHCR)
      ├── SSH into AWS EC2
      ├── Pull exact immutable image tag
      ├── Run Alembic migrations: docker run --rm $IMAGE alembic upgrade head
      ├── Update container: docker compose -f docker-compose.prod.yml up -d
      ├── Poll health check: GET /api/v1/health (with retries)
      └── Automatic rollback to .previous_image if health check fails
```

> **Important Deployment Invariant:** Code is **never built directly on the EC2 instance**. The production host pulls and runs the exact immutable Docker artifact built and verified by GitHub Actions.

---

## 2. GitHub Actions Workflows

The CI/CD pipeline is split into two workflows located under `.github/workflows/`:

### 1. Pull Request & Commit CI (`.github/workflows/ci.yml`)
Runs on every Pull Request targeting `main` and pushes to `main`:
- **`backend-ci`**:
  - Starts PostgreSQL 17 service container.
  - Installs Python 3.13 and dependencies via `uv sync --frozen`.
  - Verifies code style and imports via `uv run ruff check app tests`.
  - Verifies code formatting via `uv run ruff format --check app tests`.
  - Executes Alembic migrations against the test database: `uv run alembic upgrade head`.
  - Runs full backend test suite: `uv run pytest -v`.
- **`frontend-ci`**:
  - Sets up Node.js 22 LTS and pnpm 10.18.3.
  - Installs dependencies: `pnpm install --frozen-lockfile`.
  - Checks ESLint: `pnpm run lint`.
  - Checks TypeScript types: `pnpm run typecheck`.
  - Compiles production Next.js build: `pnpm run build`.
- **`docker-build-ci`**:
  - Builds the production multi-stage backend image: `docker build -t ramaiahmart-api:${{ github.sha }} backend/`.
  - Sanity checks container entrypoint and application module imports.

### 2. Production CD (`.github/workflows/deploy.yml`)
Runs automatically when commits land on `main`, or via manual `workflow_dispatch`:
- **Concurrency Lock:** Enforces `concurrency: group: production-deployment, cancel-in-progress: false` to ensure two deployments never run concurrently or race against each other.
- **`validate-ci`**: Runs backend linting, migrations, and test suite.
- **`build-and-push-ghcr`**:
  - Builds production Docker image using Docker Buildx.
  - Tags with immutable Git commit SHA: `ghcr.io/<owner>/ramaiahmart-api:<commit-sha>`.
  - Tags with `latest`.
  - Pushes both tags to GitHub Container Registry using `GITHUB_TOKEN`.
- **`deploy-ec2`**:
  - Authenticates to EC2 via SSH using GitHub Secrets.
  - Logs Docker into GHCR on the EC2 host.
  - Pulls the exact immutable image SHA.
  - Runs Alembic database migrations.
  - Updates the running service via `docker compose -f docker-compose.prod.yml up -d --remove-orphans api`.
  - Polls `/api/v1/health` up to 10 times (30 seconds max).
  - Automatically restores `.previous_image` if the healthcheck fails.

---

## 3. Required GitHub Secrets

Configure these secrets under **GitHub Repository → Settings → Secrets and variables → Actions**:

| Secret Name | Purpose | Example / Format |
|---|---|---|
| `EC2_HOST` | Public IP or DNS address of the AWS EC2 instance | `13.232.xxx.xxx` or `api.ramaiahmart.com` |
| `EC2_USER` | SSH username on EC2 | `ubuntu` |
| `EC2_SSH_PRIVATE_KEY` | OpenSSH private key with access to EC2 | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `EC2_SSH_PORT` | Optional custom SSH port (defaults to `22`) | `22` |

> *Note:* GitHub Container Registry authentication does not require a custom secret; it uses GitHub's built-in `GITHUB_TOKEN` with `packages: write` permissions.

---

## 4. EC2 Host Setup & Prerequisites

Before triggering the first deployment, prepare the EC2 host:

### 1. Host Directory Structure
```bash
sudo mkdir -p /srv/ramaiahmart/nginx/conf.d
sudo chown -R ubuntu:ubuntu /srv/ramaiahmart
```

Copy the following files to `/srv/ramaiahmart/`:
- `backend/docker-compose.prod.yml` → `/srv/ramaiahmart/docker-compose.prod.yml`
- `backend/nginx/nginx.conf` → `/srv/ramaiahmart/nginx/nginx.conf`
- `backend/nginx/conf.d/default.conf` → `/srv/ramaiahmart/nginx/conf.d/default.conf`
- `backend/scripts/deploy_prod.sh` → `/srv/ramaiahmart/scripts/deploy_prod.sh` (make executable: `chmod +x /srv/ramaiahmart/scripts/deploy_prod.sh`)

### 2. Production Environment File (`/srv/ramaiahmart/.env.production`)
Create `/srv/ramaiahmart/.env.production` on the EC2 host with `chmod 600`:

```ini
APP_NAME=RamaiahMart API
APP_ENV=production
DEBUG=false
API_V1_PREFIX=/api/v1

# AWS RDS PostgreSQL 17
DATABASE_URL=postgresql+psycopg://<rds_username>:<rds_password>@<rds_endpoint>:5432/<rds_database>

# Security Secrets (Generate random 64-character hex string)
JWT_SECRET_KEY=replace_with_strong_random_secret_at_least_32_characters_long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# University Restriction
ALLOWED_EMAIL_DOMAINS=msrit.edu

# AWS S3 Storage
S3_BUCKET_NAME=ramaiahmart-media-production
AWS_REGION=ap-south-1
# Leave S3_ENDPOINT_URL empty in production to use AWS S3 SDK
S3_ENDPOINT_URL=
S3_PUBLIC_ENDPOINT_URL=

# CORS Configuration (Next.js frontend URL on Vercel)
CORS_ORIGINS=["https://ramaiahmart.com","https://www.ramaiahmart.com"]

# Trusted Reverse Proxy
TRUSTED_PROXIES=["127.0.0.1","::1","10.0.0.0/8","172.16.0.0/12","192.168.0.0/16"]
```

---

## 5. Production Docker Compose (`docker-compose.prod.yml`)

The production Compose configuration runs:
1. `api`: Container running FastAPI behind Uvicorn. Exposes port 8000 only to the internal bridge network (`ramaiahmart_prod_net`).
2. `nginx`: Public-facing reverse proxy binding host ports 80 and 443, terminating TLS, rate limiting by IP/route, and forwarding requests to `api:8000`.

PostgreSQL and S3 are managed services (AWS RDS and AWS S3) external to the EC2 container stack.

---

## 6. Database Migrations

- Migrations run automatically during deployment using the freshly pulled Docker image:
  ```bash
  docker run --rm --env-file .env.production "$API_IMAGE" alembic upgrade head
  ```
- **Safety Invariant:** If the Alembic migration fails, the deployment script aborts immediately. The existing running container is **not** stopped or replaced.
- **Destructive Operations Forbidden:** Automated rollback **never** runs `alembic downgrade base`. Schema changes must be backward-compatible with the immediately preceding application version.

---

## 7. Health Check & Automated Rollback

### Healthcheck Polling
After updating the container, the deployment script polls `GET /api/v1/health` every 3 seconds for up to 10 attempts:
- A response with HTTP status `200` and `{"status": "ok"}` confirms deployment success.
- The new image tag is saved in `/srv/ramaiahmart/.current_image`.

### Automated Rollback
If the health check does not pass within 30 seconds:
1. The script reads the previously recorded image tag from `/srv/ramaiahmart/.previous_image`.
2. Restarts the container with the previous known-good tag:
   ```bash
   API_IMAGE=$(cat .previous_image) docker compose -f docker-compose.prod.yml up -d --remove-orphans api
   ```
3. Verifies that the previous version returns a healthy status.
4. Marks the GitHub Actions deployment job as **FAILED**.

### Manual Rollback Procedure
If manual operator intervention is ever needed on the EC2 host:
```bash
cd /srv/ramaiahmart

# Check previous working image
cat .previous_image

# Rollback to specific known-good image
API_IMAGE="ghcr.io/<owner>/ramaiahmart-api:<known_good_commit_sha>" \
  docker compose -f docker-compose.prod.yml up -d --remove-orphans api

# Verify status
curl -i http://localhost:80/api/v1/health
```

---

## 8. Recommended GitHub Branch Protection Settings

To ensure unverified code never lands on `main`:
1. Navigate to **GitHub Repository → Settings → Branches → Branch protection rules**.
2. Add rule for branch `main`:
   - [x] **Require a pull request before merging**
   - [x] **Require status checks to pass before merging**
     - Require: `backend-ci` (Backend Lint, Format & Tests)
     - Require: `frontend-ci` (Frontend Lint, Typecheck & Build)
     - Require: `docker-build-ci` (Docker Image Build Validation)
   - [x] **Require linear history**
   - [x] **Do not allow bypassing the above settings**

---

## 9. Local Developer Workflow

Developers can run all CI checks locally before opening a pull request:

```bash
# 1. Backend Lint & Format Check
cd backend
uv run ruff format --check app tests
uv run ruff check app tests

# 2. Backend Tests
uv run pytest -v

# 3. Frontend Checks
cd ../frontend
pnpm run lint
pnpm run typecheck
pnpm run build

# 4. Local Docker Build Verification
cd ..
docker build -t ramaiahmart-api:local backend/
```
