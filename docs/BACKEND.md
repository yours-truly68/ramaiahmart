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
