# RamaiahMart — Backend Specification

## 1. Purpose

The backend is a modular FastAPI application that owns business logic, authentication, authorization, persistence, moderation orchestration, conversations, and integrations.

The backend must remain simple enough for an MVP but structured so it can grow without a rewrite.

---

## 2. Technology

Required stack:

- Python 3.13+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- psycopg
- `uv` for dependency management
- Docker
- pytest
- Ruff

Planned integrations:

- S3-compatible object storage
- MinIO locally
- Amazon S3 in production
- Elasticsearch later
- AI moderation provider/model later

---

## 3. Architecture

Use a modular monolith.

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── logging.py
│   │
│   ├── api/
│   │   └── router.py
│   │
│   ├── models/
│   │
│   ├── schemas/
│   │
│   ├── services/
│   │
│   └── modules/
│       ├── auth/
│       ├── users/
│       ├── posts/
│       ├── categories/
│       ├── media/
│       ├── moderation/
│       └── conversations/
│
├── migrations/
├── tests/
├── Dockerfile
├── pyproject.toml
└── .env.example
```

Avoid microservices in V1.

---

## 4. Domain Entities

### User

Fields:

- id
- email
- name
- profile_image_key
- university_verified
- is_active
- created_at
- updated_at

The university domain must be configurable.

### Category

Fields:

- id
- name
- slug
- is_active
- created_at

### Post

Fields:

- id
- author_id
- type
- category_id
- title
- description
- price
- price_unit
- status
- created_at
- updated_at
- published_at

Enums:

```text
PostType:
    OFFER
    REQUEST

PostStatus:
    DRAFT
    PENDING_REVIEW
    PUBLISHED
    REJECTED
    ARCHIVED
    SOLD
    RENTED
    CLOSED
```

Do not encode future business concepts such as auction state or payment state into the initial model.

### PostImage

Fields:

- id
- post_id
- storage_key
- public_url or resolvable URL
- position
- created_at

The canonical storage key should be stored. Avoid treating a temporary presigned URL as permanent database state.

### Conversation

Fields:

- id
- post_id
- initiator_id
- owner_id
- created_at
- last_message_at
- closed_at

### Message

Fields:

- id
- conversation_id
- sender_id
- content
- created_at
- read_at

### ModerationResult

Fields:

- id
- post_id
- decision
- risk_score
- reason_codes
- provider
- model
- created_at

Store structured moderation reasons instead of only a free-form string.

---

## 5. API Design

Base path:

```text
/api/v1
```

Initial routes:

### Health

```text
GET /health
```

### Auth

```text
POST /auth/register
POST /auth/verify
POST /auth/login
POST /auth/refresh
POST /auth/logout
```

### Users

```text
GET /users/me
PATCH /users/me
GET /users/{user_id}
```

### Categories

```text
GET /categories
```

### Posts

```text
POST /posts
GET /posts
GET /posts/{post_id}
PATCH /posts/{post_id}
DELETE /posts/{post_id}
POST /posts/{post_id}/publish
POST /posts/{post_id}/close
```

### Media

```text
POST /media/upload-url
POST /media/complete
DELETE /media/{media_id}
```

The exact media API may be adjusted when implementing presigned uploads.

### Conversations

```text
POST /posts/{post_id}/conversations
GET /conversations
GET /conversations/{conversation_id}
GET /conversations/{conversation_id}/messages
POST /conversations/{conversation_id}/messages
```

---

## 6. Post Creation Flow

The intended flow:

```text
Client
  ↓
POST /posts
  ↓
Create DRAFT
  ↓
Upload media using presigned URL
  ↓
Attach media
  ↓
Submit/publish
  ↓
PENDING_REVIEW
  ↓
Moderation
  ↓
PUBLISHED / REJECTED / REVIEW
```

Do not make image uploads synchronous through the FastAPI process.

---

## 7. Storage

Local:

```text
FastAPI → MinIO
```

Production:

```text
FastAPI → Amazon S3
```

Use an abstraction such as:

```text
StorageService
├── generate_upload_url()
├── generate_download_url()
├── delete_object()
└── object_exists()
```

The rest of the application should not care whether the underlying provider is MinIO or S3.

---

## 8. Database Rules

Use SQLAlchemy 2.x declarative mappings.

Use Alembic for every schema change.

Never modify production schema manually.

Foreign keys and useful indexes must be explicit.

Initial indexes should cover:

- post.author_id
- post.category_id
- post.type
- post.status
- post.created_at
- conversation.post_id
- conversation.last_message_at
- message.conversation_id
- message.created_at

Use database constraints where they represent true invariants.

---

## 9. Authentication

V1 should use secure token-based authentication.

The implementation must support:

- password hashing if passwords are used
- access token
- refresh token
- authenticated user dependency
- authorization checks

University verification must be enforced before a user can publish a post.

Do not trust frontend role/identity fields.

---

## 10. Authorization

A user can modify/delete/close only their own posts.

A user can read a conversation only if they are a participant.

A user can send a message only if they participate in the conversation.

Moderation/admin operations must use explicit authorization.

---

## 11. Validation

Backend validation is authoritative.

Examples:

- title cannot be empty
- description cannot be empty
- OFFER must have a price/quote when required by product rules
- required images must exist before publishing
- inactive/rejected users cannot publish
- invalid category IDs must be rejected
- negative prices must be rejected
- closed posts cannot be modified into active posts without an explicit transition

Frontend validation is for UX. Backend validation is for correctness.

---

## 12. Moderation Boundary

Create a moderation service interface.

Conceptually:

```python
class ModerationService:
    async def moderate_post(...):
        ...
```

The API layer must not contain model-specific moderation logic.

Possible implementations:

```text
AIModerationService
RuleBasedModerationService
MockModerationService
```

This makes testing and provider replacement easier.

---

## 13. Error Handling

Use consistent API errors.

Example:

```json
{
  "error": {
    "code": "POST_NOT_FOUND",
    "message": "Post not found."
  }
}
```

Do not leak internal exceptions, SQL errors, stack traces, API keys, or provider details.

---

## 14. Testing

Minimum V1 coverage:

### Unit

- validation
- post state transitions
- authorization rules
- moderation decision handling

### Integration

- create post
- retrieve post
- update own post
- reject unauthorized update
- publish post
- create conversation
- send message

### API

Use FastAPI test clients and isolated test database setup.

---

## 15. Observability

V1 should include:

- structured application logs
- request IDs
- basic error logging
- health endpoint

Do not introduce a full observability stack unless required.

---

## 16. Backend Deployment

Containerize the API.

Production target:

```text
Docker
  ↓
Container registry
  ↓
AWS compute
```

PostgreSQL should be managed rather than run inside the production API container.

Images should use managed object storage.

CI/CD should:

1. install dependencies
2. run Ruff
3. run tests
4. build Docker image
5. push image
6. deploy
7. run health check

---

## 17. Backend Non-Goals

Do not introduce:

- microservices
- Kubernetes
- Celery unless asynchronous workload actually requires it
- Redis unless a concrete requirement appears
- event bus
- CQRS
- complicated repository abstractions everywhere
- vector database
- Elasticsearch before basic search requirements are validated

---

## 18. Production Reverse Proxy Architecture (Phase 1)

In production, FastAPI is never exposed directly to the public Internet. Instead, an `nginx:alpine` reverse proxy serves as the sole public gateway.

```text
Internet
  ↓ (ports 80, 443)
Nginx (nginx:alpine)
  ↓ (internal Docker network: http://backend_api:8000)
FastAPI (Uvicorn)
  ↓
PostgreSQL / MinIO / S3
```

### Network Topology & Port Exposure
- **Publicly Exposed Ports:** `80` (HTTP) and `443` (HTTPS).
- **FastAPI Port:** `8000` is bound internally only within the Docker network (`expose: ["8000"]`). In development Docker Compose, Nginx also listens on port 8000 for convenience and proxies it directly to FastAPI.
- **TLS Termination:**
  - Production TLS template is located at `backend/nginx/conf.d/ssl_production_template.conf`.
  - Mount real certificates at `/etc/nginx/certs/fullchain.pem` and `/etc/nginx/certs/privkey.pem`.
  - HTTP automatically redirects to HTTPS via 301 in production mode.
  - Strict security headers configured: HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`.

### Reverse Proxy & Sanitized Logging
- **Header Forwarding:** Nginx forwards `Host`, `X-Real-IP`, `X-Forwarded-For`, and `X-Forwarded-Proto`. It also generates or forwards `X-Request-ID`.
- **Request Size & Timeouts:** Client body size limit configured to `25M` (supporting direct image uploads/profiles while preventing memory abuse). Connect/read/send timeouts set to `60s`.
- **Sanitized Logging:** Access log format is strictly sanitized: passwords, OTPs, JWT tokens, and `Authorization` headers are scrubbed from all Nginx and FastAPI logs.

---

## 19. Rate Limiting Architecture & Policies (Phase 3)

Defense-in-depth is implemented via a dual-layer strategy: coarse IP rate limiting at Nginx, and fine-grained, context-aware rate limiting at the FastAPI application layer.

### Why Redis is Intentionally Not Used in V1
For V1's single-instance deployment, Redis introduces unnecessary operational complexity, memory overhead, and maintenance burden. Instead, an in-process, thread-safe sliding window rate limiter (`InMemoryRateLimiterStorage`) is used.
It implements the `RateLimiterStorage` protocol (`check_and_record`, `record_failure`, `get_failures`, `reset`, `increment_attempts`), ensuring a seamless drop-in migration to Redis (`RedisRateLimiterStorage`) when multi-instance scaling is required without modifying route handlers.

### Layer 1: Nginx Coarse Protection
- Global API limit: `30 req/s` (burst 50) using `limit_req_zone $binary_remote_addr`.
- Auth endpoints coarse throttle: `15 req/m` (burst 10) to stop volumetric bot attacks.
- Connection limit: max 20 concurrent connections per IP.
- Healthcheck endpoint (`/api/v1/health`): exempt from rate limiting for reliable monitoring.

### Layer 2: FastAPI Context-Aware Protection
Campus networks route hundreds of students through shared NAT public IPs. FastAPI's `RateLimiter` balances abuse prevention with campus NAT tolerance:

1. **Login (`POST /api/v1/auth/login`)**:
   - IP policy: 15 failed attempts per 15 minutes (generous for campus NAT).
   - Account policy: 5 failed attempts per 15 minutes per email (prevents credential stuffing).
   - Only *failed* attempts count against the limit. Successful logins reset the email failure counter.
   - Does not reveal whether an email exists.
2. **Registration (`POST /api/v1/auth/register`)**:
   - IP policy: 10 registrations per hour per IP (supports dorm/lab setups while preventing mass bot registrations).
   - Restricted strictly to `@msrit.edu` university domain.
3. **Token Refresh (`POST /api/v1/auth/refresh`)**:
   - 30 requests/minute per IP, ensuring smooth client token refreshes without disruption.
6. **Standard Error Response**:
   When rate limited, returns HTTP 429 with `Retry-After: <seconds>` header:
   ```json
   {
     "error": {
       "code": "RATE_LIMITED",
       "message": "Too many requests. Please try again later."
     }
   }
   ```

### Proxy-Aware Client IP Extraction
To prevent header spoofing from untrusted public clients, FastAPI's `get_client_ip` validates that the direct client connection is from a trusted proxy subnet (e.g. `127.0.0.1`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, configurable via `TRUSTED_PROXIES`) before inspecting `X-Forwarded-For` or `X-Real-IP`.

---

## 20. Production Configuration & Secrets Enforcement

To prevent security vulnerabilities:
- **JWT Secret Key:** `JWT_SECRET_KEY` must be at least 32 characters in production. If set to default or insecure values when `APP_ENV=production`, the application raises a `RuntimeError` and terminates startup immediately.
- **Debug Mode:** `DEBUG=True` is strictly disallowed in production mode.
- **No Committed Secrets:** Credentials, private keys, and secrets are passed exclusively via environment variables.

---

## 21. Account Lifecycle, Deletion & Disaster Recovery Backup (Phase 5)

### Account Status State Machine
- `ACTIVE`: Normal operating state.
- `INACTIVE`: After 90 days without meaningful activity. Non-destructive; no suspension, no loss of posts/messages. Reactivates immediately to `ACTIVE` upon any meaningful authenticated activity.
- `DELETION_PENDING`: Triggered by `POST /api/v1/users/me/deletion-request`. Account enters a strict 15-day grace period.

```text
ACTIVE  ────────(90 days inactivity)───────>  INACTIVE
  │                                               │
  │ <──────(meaningful activity / login)──────────┘
  │
  ├───────(POST deletion-request)───────────>  DELETION_PENDING
  │                                               │
  │ <──────(login / meaningful activity / cancel)─┤
  │                                               │ (15 days no activity)
  │                                               v
  └───────────────────────────────────────> PERMANENT DELETION
```

### Meaningful Activity Tracking
Meaningful activity is tracked centrally via `record_user_activity(user, db)`:
- **Qualifying events:** Login, creating a post, editing a post, publishing a post, closing a post, sending a conversation message, updating profile details, cancelling deletion.
- **Excluded:** Token refresh, anonymous browsing, GET requests, loading feeds or profile views, health checks.

### Deletion & Object Storage Cleanup
- **Grace Period (15 Days):** If a user logs in or performs any meaningful activity during the 15-day grace period, pending deletion is immediately cancelled.
- **Permanent Purge:** Accounts where `status == DELETION_PENDING` and `deletion_scheduled_at <= now()` are processed:
  1. Storage objects (`user.profile_image_key`, all post images) are removed from S3/MinIO. Missing objects do not fail the deletion.
  2. Relational data (User, Posts, Conversations, Messages, Legal Consents, Verification Codes, Tokens) is removed cleanly via cascade.
  3. Operation is idempotent and retryable on failure.

### Disaster-Recovery Backup Synchronization
- **Retention:** Rolling 7-day backup retention.
- **Authoritative Reconciliation:** The disaster recovery backup mirrors the current production database. Accounts permanently deleted in production are omitted from the next backup generation.
- **Fault-Tolerant Promotion:** A new backup generation is verified before promotion; previous known-good backups remain intact if a backup cycle fails.

