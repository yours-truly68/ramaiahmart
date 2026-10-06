# 🎓 RamaiahMart

> **A secure, verified peer-to-peer campus marketplace built exclusively for students, faculty, and the campus community of Ramaiah Institute of Technology (MSRIT).**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Next.js](https://img.shields.io/badge/Next.js-16.3-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791?logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)](https://www.docker.com/)
[![CI Status](https://img.shields.io/badge/CI-Passing-brightgreen?logo=github-actions)](https://github.com/yours-truly68/ramaiahmart/actions)
[![Open Source Love](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)](https://github.com/ellerbrock/open-source-badges/)

---

## 📌 Table of Contents

- [About RamaiahMart](#-about-ramaiahmart)
- [Who Is This Product For?](#-who-is-this-product-for)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Important Architectural & Engineering Decisions](#-important-architectural--engineering-decisions)
- [Local Development Setup](#-local-development-setup)
  - [Prerequisites](#prerequisites)
  - [Option A: Running with Docker Compose (Recommended)](#option-a-running-with-docker-compose-recommended)
  - [Option B: Running Services Natively](#option-b-running-services-natively)
- [Running Tests & Quality Assurance](#-running-tests--quality-assurance)
- [Project Directory Structure](#-project-directory-structure)
- [Open Source & Community Contributions](#-open-source--community-contributions)
- [License](#-license)

---

## 📖 About RamaiahMart

University campuses are bustling micro-economies. Every semester, thousands of students buy and sell textbooks, engineering drawing kits, lab coats, electronic components, hostel furniture, bicycles, calculators, and study notes.

Traditional platforms (OLX, Facebook Marketplace, generic WhatsApp groups) suffer from critical flaws:
- **Spam & Scams:** Anyone on the internet can message students or post fake listings.
- **Lost Context:** WhatsApp chats get buried in endless group threads with no search, filters, or price sorting.
- **Privacy Leaks:** Phone numbers and personal details are publicly exposed to unverified outsiders.

**RamaiahMart** solves this by establishing a trusted, closed-loop student marketplace where only authenticated students and faculty can participate. It combines modern e-commerce ergonomics with ironclad campus safety.

---

## 🎯 Who Is This Product For?

1. **Students:**
   - Buy seniors' textbooks, notes, and lab equipment at student-friendly prices.
   - Sell used furniture, appliances, or gadgets when moving out of hostels or PGs.
   - Post **"Requests"** when looking for specific course materials or finding campus flatmates.
2. **Incoming Freshmen:**
   - Quickly acquire essential first-year kits, calculators, and verified study material without overpaying at retail shops.
3. **Faculty & Staff:**
   - Exchange academic resources, books, and household goods within a trusted campus community.

---

## ✨ Key Features

- **🎓 Campus-Verified Access:** Strict domain restriction (`@msrit.edu`) ensures only authorized students and faculty join.
- **🏷️ Dual Marketplace Feed:** Explicit separation between **Offers** (*"I have this for sale"*) and **Requests** (*"I am looking for this"*).
- **💬 Direct In-App Conversations:** Participant-only private messaging with unread badges, read timestamps, and race-condition-safe chat threads.
- **📲 Optional WhatsApp Inquiries:** Sellers can opt to share WhatsApp contact details with auto-formatted, pre-filled inquiry messages.
- **🖼️ Secure Media Uploads:** Direct-to-storage presigned uploads with server-side magic-byte detection (JPEG, PNG, WebP) and 10 MB limits.
- **🛡️ Two-Stage AI Content Moderation:**
  - *Automated Text Review:* Pre-publication title/description scan via LLM to block abusive, illegal, or commercial spam.
  - *Reactive Vision Review:* Automated image analysis triggered strictly when listings are reported for explicit or mismatched imagery.
- **🚩 Student Reporting & Safety:** Structured reporting mechanism with anti-abuse deduplication, rate limits, and author immunity checks.
- **🔒 Account Lifecycle & Data Privacy:** Full compliance with data privacy, 15-day deletion grace periods with instant reactivation, and strict cookie-based session management.
- **📱 Responsive & Accessible UI:** Mobile-first, fully responsive design tested from 320px mobile screens to large desktop monitors.

---

## 🛠️ Tech Stack

### Frontend
- **Framework:** [Next.js 16](https://nextjs.org/) (App Router, Server Components & Turbopack)
- **Language:** TypeScript 5.8
- **UI & State:** React 19, [TanStack Query v5](https://tanstack.com/query) for server state caching
- **Styling:** Vanilla CSS design system with CSS custom properties, responsive utility classes, and custom tokens
- **Icons:** [Lucide React](https://lucide.dev/)
- **Typography:** Local high-legibility Satoshi fonts

### Backend & API
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.13)
- **Data Validation:** [Pydantic v2](https://docs.pydantic.dev/) & `pydantic-settings`
- **Database ORM:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (modern declarative mapped classes)
- **DB Driver:** [psycopg 3](https://www.psycopg.org/) (high-performance asynchronous/synchronous PostgreSQL driver)
- **Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
- **Package Management:** [uv](https://docs.astral.sh/uv/) (blazing-fast Python package manager)
- **Code Hygiene:** [Ruff](https://docs.astral.sh/ruff/) (linter and code formatter)

### Database & Storage
- **Primary Database:** PostgreSQL 17
- **Object Storage:** MinIO (local development) / AWS S3 (production) via `boto3`

### Infrastructure & Reverse Proxy
- **Gateway / Proxy:** Nginx (Alpine) with campus-NAT-aware rate limiting, TLS termination, and sanitized logging
- **API Boundary:** Next.js same-origin API proxy (`/api/market/*`) with CSRF origin validation
- **Containerization:** Multi-stage, non-root Docker images
- **CI/CD:** GitHub Actions (linting, typechecking, database migration checks, and full regression test execution)

---

## 🏛️ Important Architectural & Engineering Decisions

### 1. Same-Origin Frontend API Proxy (`/api/market/*`)
Browser clients never make direct requests to the backend API or store JWT access/refresh tokens in `localStorage`. Instead, Next.js handles server-to-server proxying:
- Tokens are held in secure, `HttpOnly`, `SameSite=Lax` cookies.
- An explicit regex allowlist permits only canonical V1 marketplace endpoints (blocking unvetted routes).
- State-mutating requests (`POST`, `PATCH`, `DELETE`) require matching `Origin` or `Referer` headers, guaranteeing CSRF immunity.

### 2. Direct-to-S3 Presigned Uploads with Server-Side Validation
Large image uploads do not pipe multi-megabyte payloads through the application server:
1. Client requests a presigned PUT URL with an auto-generated UUID storage key (`posts/{post_id}/{uuid}.jpg`).
2. Client uploads directly to MinIO/S3.
3. On `/media/complete`, the backend performs an S3 HTTP Range request (`bytes=0-511`) to inspect magic bytes (preventing spoofed `.jpg` shell scripts) and checks real object size against 10 MB limits.
4. Any rejected upload is immediately deleted from S3 storage to prevent orphaned junk.

### 3. Deliberate V1 Operational Simplicity (No Redis, No WebSockets)
To keep the application robust, deployable on a single low-cost virtual server (e.g., AWS EC2 t4g.small or Lightsail), and virtually zero-maintenance:
- **Rate Limiting:** Managed in-memory with sliding time windows and configured for university NAT bursts.
- **Chat:** High-efficiency HTTP polling with TanStack Query instead of complex stateful WebSocket clusters.
- **Zero Microservice Sprawl:** Clean modular monolith architecture.

### 4. Cost-Conscious, Two-Provider AI Moderation
- **Text Moderation:** Triggered automatically upon post publication using low-latency LLM inference (e.g., Groq / OpenAI).
- **Vision Moderation:** Never run indiscriminately on every uploaded photo. Instead, vision AI (e.g., Vercel AI Gateway) runs **reactively** only when a student reports a listing for `EXPLICIT_IMAGE` or `IMAGE_MISMATCH`.

### 5. Manual Password Recovery
Automated email sending (e.g., SendGrid, Resend) requires dedicated domain reputation and credit card costs that frequently fail on student university addresses. V1 uses verified manual out-of-band identity confirmation via student ID cards, keeping delivery guarantees at 100% with zero credential exposure.

---

## 🚀 Local Development Setup

### Prerequisites

Make sure you have installed on your machine:
- **Docker & Docker Compose** (Docker Desktop or Docker Engine)
- **Node.js** (v22+ LTS recommended) & **pnpm** (v10.x)
- **Python 3.13** & **uv** (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

---

### Option A: Running with Docker Compose (Recommended)

This spins up PostgreSQL, MinIO, FastAPI, and Nginx in containers with health checks:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yours-truly68/ramaiahmart.git
   cd ramaiahmart
   ```

2. **Start the backend stack:**
   ```bash
   cd backend
   docker compose up -d --build
   ```

3. **Run database migrations and seed categories:**
   ```bash
   # Run migrations to head
   docker compose exec api alembic upgrade head

   # Seed default marketplace categories (Electronics, Books, Housing, etc.)
   uv run python -m scripts.seed_categories
   ```

4. **Ensure the MinIO storage bucket exists:**
   ```bash
   docker compose exec minio mc alias set myminio http://localhost:9000 minioadmin minioadmin
   docker compose exec minio mc mb myminio/ramaiahmart-media --ignore-existing
   ```

5. **Start the Next.js frontend:**
   ```bash
   cd ../frontend
   pnpm install --frozen-lockfile
   cp .env.example .env.local
   pnpm dev
   ```

6. **Open your browser:**
   - 🌐 **Frontend Web App:** [http://localhost:3000](http://localhost:3000)
   - 🔌 **API Gateway (via Nginx):** [http://localhost:8000](http://localhost:8000)
   - 📑 **FastAPI Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
   - 🗄️ **MinIO Web Console:** [http://localhost:9101](http://localhost:9101) *(User: `minioadmin`, Pass: `minioadmin`)*

---

### Option B: Running Services Natively

If you prefer running FastAPI directly on your host machine without Docker:

1. **Start local PostgreSQL and MinIO instances:**
   - Ensure PostgreSQL is running on port `5432` with database `ramaiahmart`.
   - Ensure MinIO is running on port `9100`.

2. **Configure and start the Backend:**
   ```bash
   cd backend
   cp .env.example .env
   uv sync
   uv run alembic upgrade head
   uv run python -m scripts.seed_categories
   uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

3. **Configure and start the Frontend:**
   ```bash
   cd ../frontend
   cp .env.example .env.local
   pnpm install
   pnpm dev
   ```

---

## 🧪 Running Tests & Quality Assurance

RamaiahMart maintains high test coverage with automated regression suites across both backend and frontend.

### Backend Verification
From the `backend/` directory:
```bash
# Run complete test suite (100+ tests including IDOR, XSS, rate-limiting, and upload security)
uv run pytest -v

# Run code linting
uv run ruff check app tests

# Run format validation
uv run ruff format --check app tests

# Check for database schema drift
uv run alembic check
```

### Frontend Verification
From the `frontend/` directory:
```bash
# Lint frontend code with ESLint (zero warnings allowed)
pnpm run lint

# Check TypeScript types
pnpm run typecheck

# Run automated security, CSP, and API proxy boundary tests
pnpm run test:security

# Build production Next.js bundle
pnpm run build
```

---

## 📂 Project Directory Structure

```text
ramaiahmart/
├── .github/
│   └── workflows/
│       ├── ci.yml               # GitHub Actions CI (lint, tests, build, drift)
│       └── deploy.yml           # Automated production deployment pipeline
├── backend/
│   ├── alembic/                 # Database migration versions & env
│   ├── app/
│   │   ├── api/                 # API routes & dependency injection
│   │   │   └── v1/              # Auth, Posts, Media, Chat, Reports, Legal
│   │   ├── core/                # Config, JWT security, proxy, rate limiter
│   │   ├── db/                  # Session management & Base model
│   │   ├── models/              # SQLAlchemy models (User, Post, Chat, etc.)
│   │   ├── schemas/             # Pydantic request/response validation
│   │   └── services/            # Storage (S3), Moderation (AI), Lifecycle
│   ├── nginx/                   # Nginx reverse proxy configurations
│   ├── scripts/                 # Maintenance, migration & taxonomy seeds
│   ├── tests/                   # Pytest test suite (100% green)
│   ├── Dockerfile               # Multi-stage production container
│   ├── docker-compose.yml       # Local development stack
│   └── pyproject.toml           # Python dependencies & Ruff config
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router (feed, auth, chat, legal)
│   │   │   └── api/market/      # Same-origin hardened API proxy
│   │   ├── components/          # Accessible UI primitives & layout
│   │   ├── features/            # Marketplace, Account, Chat, Posting
│   │   └── lib/                 # API client, tokens, security helpers
│   ├── scripts/                 # Automated security & proxy test runners
│   ├── next.config.ts           # Authoritative Content Security Policy
│   ├── package.json             # Frontend dependencies & scripts
│   └── tsconfig.json            # Strict TypeScript configuration
├── docs/                        # Architecture, deployment & security guides
└── README.md                    # Project documentation (you are here)
```

---

## 🤝 Open Source & Community Contributions

RamaiahMart is **100% Free and Open Source Software (FOSS)**. 

We believe that university software should be open, transparent, and built by the very students who use it every day. Whether you are fixing a typo, improving mobile UI responsiveness, adding a new accessibility feature, optimizing database queries, or identifying security edge cases — **your contributions are warmly welcomed!**

### How to Contribute

1. **Fork the Repository:** Click the `Fork` button at the top right of this page.
2. **Clone your Fork:**
   ```bash
   git clone https://github.com/<your-username>/ramaiahmart.git
   cd ramaiahmart
   ```
3. **Create a Feature Branch:**
   ```bash
   git checkout -b feature/amazing-feature
   # or
   git checkout -b fix/issue-description
   ```
4. **Make Your Changes & Run Checks:**
   Ensure all tests pass before committing:
   ```bash
   # Backend
   cd backend && uv run pytest -q && uv run ruff check .

   # Frontend
   cd ../frontend && pnpm run test:security && pnpm run lint && pnpm run typecheck
   ```
5. **Commit with Conventional Messages:**
   ```bash
   git commit -m "feat: add category filter count badge"
   # or
   git commit -m "fix: resolve mobile navbar padding on iOS"
   ```
6. **Push and Open a Pull Request:**
   Push your branch to GitHub and submit a Pull Request describing your changes and testing steps.

---

## 📜 License

RamaiahMart is open-source software licensed under the **[MIT License](LICENSE)**. You are free to inspect, modify, fork, and self-host this project.

---

<div align="center">
  <b>Built with ❤️ by students, for students of Ramaiah Institute of Technology.</b><br>
  <sub>Have questions, ideas, or feedback? Open an issue on GitHub or reach out to the campus maintainers.</sub>
</div>
