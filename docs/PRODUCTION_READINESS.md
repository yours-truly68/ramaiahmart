# RamaiahMart Backend — Production Readiness Report

**Date:** October 5, 2026  
**Application:** RamaiahMart FastAPI Backend  
**Deployment Target:** Docker on AWS EC2, AWS RDS PostgreSQL, AWS S3  
**Status:** **READY FOR DEPLOYMENT CONFIGURATION**

---

## 1. Executive Summary

A comprehensive architectural, security, and performance review of the RamaiahMart backend was completed. The backend foundation has been hardened without introducing unnecessary complexity, microservices, Kubernetes, Redis, or Celery. All 35 tests pass with sub-4-second test execution.

---

## 2. Critical Issues Found & Fixed

### Security
| Issue Identified | Risk Severity | Fix Implemented |
|---|---|---|
| **Missing CORS Configuration** | **High** | Added `CORSMiddleware` with configurable allowed origins (`CORS_ORIGINS`) defaulting to frontend ports, rejecting unauthorized origins while enabling standard HTTP methods and credentials. |
| **Missing HTTP Security Headers** | **High** | Injected `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, and `HSTS` (when HTTPS is enabled). |
| **Unhandled Exception Information Leakage** | **Medium** | Implemented a global catch-all exception handler returning structured `{"error": {"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred. Please try again later."}}` with `X-Request-ID` without leaking Python stack traces or DB errors. |
| **Missing Request Traceability** | **Medium** | Added middleware that generates or preserves `X-Request-ID` correlation identifiers for end-to-end request tracing across reverse proxies. |
| **Sensitive Data Exposure in Logs** | **Medium** | Implemented structured logging capturing HTTP method, path, status, latency (`duration_ms`), and client IP while explicitly omitting request bodies, passwords, tokens, and verification codes. |

### Database & Concurrency
| Issue Identified | Risk Severity | Fix Implemented |
|---|---|---|
| **Default Connection Pool Under Provisioning** | **High** | Configured production-grade connection pooling with `pool_size=10`, `max_overflow=20`, `pool_timeout=30s`, `pool_recycle=1800s`, and `pool_pre_ping=True` configurable via environment variables for AWS RDS. |
| **Session Rollback on Route Exception** | **High** | Hardened `get_db()` dependency generator with `except Exception: db.rollback(); raise` ensuring incomplete transactions are cleanly rolled back when requests fail. |
| **Cascade Deletion Verification** | **Medium** | Verified database foreign keys with `ondelete="CASCADE"` properly purge associated `conversations`, `messages`, `post_images`, and `moderation_results` when posts or users are deleted. |

### Docker & Packaging
| Issue Identified | Risk Severity | Fix Implemented |
|---|---|---|
| **Bloated Multi-stage Image Copy** | **Medium** | Replaced separate `COPY` followed by `RUN chown -R appuser:appgroup /app` with a single `COPY --chown=appuser:appgroup` step, reducing image layer redundancy and build times. |
| **Missing Container Healthcheck** | **Medium** | Added lightweight, native Python healthcheck (`urllib.request`) in Dockerfile querying `/api/v1/health` with zero apt package bloat. |
| **Proxy Header Client IP Stripping** | **High** | Configured uvicorn startup command with `--proxy-headers --forwarded-allow-ips=*` to properly resolve client IP and scheme behind AWS ALB / EC2 reverse proxies. |

---

## 3. Architecture & Security Invariant Summary

1. **Authentication & Passwords:**
   - Passwords hashed using bcrypt with salt rounds.
   - Long-lived refresh tokens stored as SHA-256 hashes with database revocation support (`revoked_at`).
   - University verification enforced via OTP and strict domain whitelisting (`ALLOWED_EMAIL_DOMAINS`).
2. **Post Lifecycle & Direct Storage:**
   - Image binaries never stream through FastAPI. Browsers upload directly to S3/MinIO via time-limited presigned PUT URLs.
   - Storage keys strictly enforce post namespace prefix (`posts/{post_id}/{uuid}.{ext}`).
   - Direct-to-storage completion validates object existence in S3 before recording metadata in PostgreSQL.
3. **Pluggable Moderation:**
   - Moderation decoupled into `ModerationProvider` protocol and `ModerationService`.
   - Fail-closed design: any provider failure automatically falls back to `REVIEW` (`PENDING_REVIEW`), never silently publishing a listing.

---

## 4. Remaining Risks & Mitigation

| Area | Current Risk | Recommended Mitigation |
|---|---|---|
| **Public Rate Limiting** | While endpoints validate input strictly, unauthenticated endpoints (`POST /auth/login`, `POST /auth/register`) can be subject to credential brute force without network-level rate limiting. | Deploy AWS WAF (or AWS CloudFront rate limiting / Nginx rate limiting) in front of the EC2 instance. |
| **Single-node Process Concurrency** | The current Docker container runs a single Uvicorn process. | On larger multi-core EC2 instances (e.g. `t4g.small` or `c7g.medium`), run Uvicorn with `--workers 2` or `--workers 4`. |
| **MinIO vs AWS S3 CORS** | Local MinIO allows direct PUT uploads; AWS S3 buckets in production require a Bucket CORS configuration allowing PUT requests from the frontend domain. | Apply S3 Bucket CORS policy during AWS S3 provisioning. |

---

## 5. Deployment Prerequisites for AWS

Before running `docker run` or `docker compose` on the target EC2 instance:

1. **AWS RDS (PostgreSQL 17):**
   - Provision a PostgreSQL RDS instance in the same VPC as the EC2 instance.
   - Security group rule allowing port 5432 inbound from EC2 security group only.
   - Run Alembic migrations: `alembic upgrade head`.

2. **AWS S3 Bucket:**
   - Create private S3 bucket (e.g., `ramaiahmart-media-production`).
   - Block public access enabled (presigned URLs bypass public access restrictions securely).
   - Set S3 CORS configuration:
     ```json
     [
       {
         "AllowedHeaders": ["*"],
         "AllowedMethods": ["PUT", "GET", "HEAD"],
         "AllowedOrigins": ["https://ramaiahmart.com"],
         "ExposeHeaders": ["ETag"]
       }
     ]
     ```
   - EC2 IAM Instance Role with `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`, `s3:HeadObject` permissions (avoid hardcoded keys in `.env`).

3. **Production Environment Variables (`.env.production`):**
   ```ini
   APP_NAME=RamaiahMart API
   APP_ENV=production
   DEBUG=false
   DATABASE_URL=postgresql+psycopg://<rds_user>:<rds_password>@<rds_host>:5432/ramaiahmart
   JWT_SECRET_KEY=<generate_random_64_char_hex_key>
   ALLOWED_EMAIL_DOMAINS=ramaiah.edu,msrit.edu
   CORS_ORIGINS=https://ramaiahmart.com
   S3_BUCKET_NAME=ramaiahmart-media-production
   AWS_REGION=ap-south-1
   # Leave S3_ENDPOINT_URL empty in production to default to AWS S3 SDK
   S3_ENDPOINT_URL=
   S3_PUBLIC_ENDPOINT_URL=
   ```

---

## 6. Recommended Next Steps

1. **Frontend Integration:**
   - Initialize the Next.js frontend in `frontend/`.
   - Implement authentication views, marketplace feed, direct image upload hook via presigned URLs, and post creation flow.
2. **Reverse Proxy & SSL:**
   - Configure AWS ALB or Caddy / Nginx on EC2 with Let's Encrypt SSL certificates.
3. **CI/CD Pipeline:**
   - Add GitHub Actions workflow to run `uv run ruff check .` and `uv run pytest` on PRs, build multi-arch Docker image, and deploy to EC2.
