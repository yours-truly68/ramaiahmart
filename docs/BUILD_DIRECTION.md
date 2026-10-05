# RamaiahMart — Build Direction

## 1. Objective

Build RamaiahMart quickly enough to validate the idea with real Ramaiah students while maintaining a clean production-grade foundation.

The strategy is:

> Use AI to accelerate implementation, but keep architecture, product scope, and acceptance criteria controlled.

AI coding agents may implement code, but they must follow these documents as the source of truth.

---

## 2. Source of Truth

Priority order:

1. `docs/PRODUCT.md`
2. `docs/BACKEND.md`
3. `docs/FRONTEND.md`
4. `docs/BUILD_DIRECTIONn.md`

If an implementation decision conflicts with Product.md, Product.md wins.

If a coding agent wants to introduce a new major dependency, service, database, architecture pattern, or feature, it should stop and request approval rather than silently expanding scope.

---

## 3. V1 Scope

Build only:

### Authentication

- University student verification
- Login
- Profile

### Marketplace

- Browse posts
- Search
- Categories
- Post details
- OFFER / REQUEST distinction

### Posting

- Create OFFER
- Create REQUEST
- Product/service name
- Description
- Image
- Price/quote
- Publish

### Moderation

- Basic rule checks
- AI moderation boundary
- PENDING_REVIEW
- APPROVED/PUBLISHED
- REJECTED/REVIEW

### Conversations

- Start conversation from post
- Send messages
- View conversations
- Post context inside conversation

### Infrastructure

- PostgreSQL
- MinIO locally
- S3-compatible storage abstraction
- Docker
- CI
- Production deployment path

---

## 4. Explicitly Do Not Build

Do not implement unless Product.md is explicitly updated:

- Payments
- Auctions
- Bidding
- Offers/negotiation
- Delivery
- Escrow
- Automated matching
- Recommendation engine
- Semantic search
- WhatsApp API
- Separate buyer/seller accounts
- Microservices

---

## 5. Implementation Strategy

Build in vertical slices.

Do not implement the entire backend, then the entire frontend.

### Slice 1 — Infrastructure

Deliver:

- repository structure
- FastAPI starts
- Next.js starts
- PostgreSQL runs
- MinIO runs
- environment configuration
- Docker Compose
- health endpoint

Acceptance:

```text
docker compose up
```

starts required local infrastructure.

---

### Slice 2 — Database

Implement:

- User
- Category
- Post
- PostImage

Create Alembic migrations.

Acceptance:

- migration applies cleanly
- migration rollback works in development
- basic database constraints work

---

### Slice 3 — Posts API

Implement:

```text
POST /posts
GET /posts
GET /posts/{id}
PATCH /posts/{id}
DELETE /posts/{id}
```

Acceptance:

- authenticated user can create a post
- post appears in feed
- unauthorized users cannot modify another user's post

---

### Slice 4 — Frontend Feed

Implement:

- homepage
- search input
- category navigation
- post cards
- post detail page

Acceptance:

A user can browse real database-backed posts.

---

### Slice 5 — Post Creation

Implement:

- I HAVE
- I NEED
- conversational creation UI
- image upload
- price/quote
- publish

Acceptance:

A student can create a post in under a minute.

---

### Slice 6 — Moderation

Implement moderation service boundary.

Start with deterministic rules and a mock/placeholder provider if the final AI provider is not yet selected.

Acceptance:

- every post passes through moderation state
- rejected posts are not publicly visible
- moderation decisions are persisted

---

### Slice 7 — Authentication

Implement:

- university verification
- login
- authenticated routes
- profile

Acceptance:

Only verified students can publish.

---

### Slice 8 — Conversations

Implement:

- conversation creation from a post
- message list
- send message
- unread/read state

Acceptance:

Two users can communicate about a specific post.

---

### Slice 9 — Production Deployment

Frontend:

```text
Vercel
```

Backend:

```text
Docker
↓
AWS compute
```

Database:

```text
Managed PostgreSQL / RDS
```

Images:

```text
Amazon S3
```

CI/CD:

```text
GitHub Actions
```

---

## 6. AI Coding Agent Rules

When using Claude Code, Cursor, Codex, or another coding agent:

### Before changing architecture

Read:

- Product.md
- BACKEND.md
- FRONTEND.md
- build_direction.md

### Before implementing a feature

State:

1. What is being implemented.
2. Which files will change.
3. What API/data model changes are required.
4. How it will be tested.
5. What is explicitly not being changed.

Then implement.

### After implementation

The agent should:

- run formatting/linting
- run tests
- verify type checking where applicable
- report failures
- not hide errors
- not silently remove tests
- not silently weaken validation

---

## 7. Engineering Rules

### Backend

- Business logic belongs in services/modules.
- Routers should remain thin.
- Pydantic validates external input.
- SQLAlchemy handles persistence.
- Alembic owns schema migrations.
- Do not expose database models directly as API contracts.
- Use explicit authorization checks.
- Never trust client-supplied identity.
- Do not store image binaries in PostgreSQL.

### Frontend

- Server state belongs in TanStack Query.
- Avoid unnecessary global state.
- API contracts should be typed.
- Components should not contain backend business rules.
- Forms should have clear validation and error states.
- Avoid giant components.

### General

- Prefer simple code over abstractions without a current need.
- Avoid premature optimization.
- Avoid premature distributed architecture.
- Avoid speculative dependencies.
- Keep commits focused.

---

## 8. Git Strategy

Use a simple strategy:

```text
main
```

for production.

Feature branches:

```text
feature/auth
feature/posts
feature/conversations
feature/moderation
```

Every merge to `main` should pass CI.

Avoid maintaining a complicated multi-environment branch structure until it becomes necessary.

---

## 9. CI Pipeline

Every pull request should run:

```text
Install
  ↓
Lint
  ↓
Type checks
  ↓
Tests
  ↓
Build
```

Main branch:

```text
CI
 ↓
Docker build
 ↓
Push image
 ↓
Deploy
 ↓
Health check
```

Frontend deployment can be handled by Vercel's Git integration initially.

---

## 10. Environment Configuration

Never commit secrets.

Use:

```text
.env.example
```

and environment variables for:

- database URL
- JWT configuration
- storage credentials
- storage endpoint
- bucket name
- AI provider credentials
- application URL

Production secrets must be stored in the hosting platform's secret manager/environment configuration.

---

## 11. Definition of Done

A feature is not complete because code exists.

It is complete when:

- implementation exists
- validation exists
- authorization is correct
- error states are handled
- tests cover important behavior
- frontend handles loading/error/empty states
- lint/type checks pass
- documentation is updated when behavior changes
- feature works locally
- deployment path remains valid

---

## 12. Product Feedback Loop

After launch, prioritize based on behavior.

Measure:

```text
Visitors
↓
Posts viewed
↓
Posts created
↓
Conversations started
↓
Repeat usage
```

Look for unmet demand.

Examples:

```text
Many users search "bike"
Few bike offers
→ improve vehicle category / demand discovery

Many conversations ask "can you lower the price?"
→ consider Offers in V2

Many users request rentals
→ improve rental metadata

Many requests have matching offers
→ consider automated matching
```

Do not add features simply because competitors have them.

---

## 13. Design Direction

Use the provided visual reference as the product's design north star.

Desired feeling:

> Warm, editorial, youthful, campus-native, premium but approachable.

Avoid making the application look like:

- OLX
- eBay
- Facebook Marketplace
- a generic SaaS admin dashboard

The marketplace should feel like a product with a strong identity.

---

## 14. Current Build Priority

The immediate sequence is:

```text
1. Repository + docs
2. Local infrastructure
3. Backend foundation
4. Database
5. Posts API
6. Frontend shell
7. Feed
8. Post creation
9. Image storage
10. Authentication
11. Moderation
12. Conversations
13. CI/CD
14. Production deployment
15. Observe real users
```

Do not optimize for feature count.

Optimize for getting the first real students through:

```text
SIGN UP
  ↓
SEE POSTS
  ↓
POST SOMETHING
  ↓
DISCOVER SOMETHING
  ↓
START A CONVERSATION
```

That is the V1.
