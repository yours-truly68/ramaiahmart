# RamaiahMart frontend

The homepage at `/` is the real campus marketplace feed. `/design-system` remains the component specimen.

## Run

Use Node.js 24 LTS and pnpm 10.18.3. Start PostgreSQL and the FastAPI backend first. From `backend/`:

```sh
.venv/bin/alembic upgrade head
.venv/bin/python -m scripts.seed_categories
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The category seed is idempotent and adds only the nine initial categories; it does not add listings or modify existing data. Database configuration is documented in `backend/.env.example`.

From `frontend/`:

```sh
pnpm install --frozen-lockfile
cp .env.example .env.local
pnpm dev
```

Open http://localhost:3000. Set server-only `API_BASE_URL` when FastAPI is hosted elsewhere; the default is `http://127.0.0.1:8000/api/v1`. No backend credential or infrastructure URL is embedded in the browser bundle.

```sh
pnpm lint
pnpm build
```

## Homepage behavior and API contract

- TanStack Query loads `/categories` and paginated `/posts` through the same-origin `/api/market` boundary.
- `GET /posts` accepts `q`, `category_slug`, `category_id`, `type` (`OFFER`/`REQUEST`), `page`, and `page_size`. `q` is a case-insensitive literal substring of title or description, limited to 200 characters. The response is `{ items, total, page, page_size, pages }`; only published posts are returned, ordered by creation time and ID descending.
- The feed separates Offers (the default) and Requests; there is no combined view. Clearing search/category filters preserves the selected type. Search and category/type filters are reflected in the page URL. More posts uses backend page numbers; each request loads 12 posts. A card opens a native accessible dialog, fetching `GET /posts/{id}`. The `post` query parameter supports direct links and browser navigation.
- Cards use the API’s `images[].public_url`, ordered by `position`, with image-failure/no-photo fallbacks. Prices are decimal strings formatted in INR. `price_unit`, category, type, and timestamps come directly from the response. The backend does not expose location, so no location is invented.
- Category names and IDs come from the API. Presentation hints assign the initial nine slugs their icon, color, and order. Additional backend categories remain selectable in the feed and draft form.
- Post Item, I HAVE, I NEED, and mobile posting actions lead to `/post/create`, optionally preselecting OFFER or REQUEST.
- `/login` and `/register` use the real backend authentication and verification endpoints. Both access and refresh tokens stay in server-set HttpOnly, SameSite=Lax cookies (Secure in production). The proxy refreshes expired access sessions, clears invalid sessions, and revokes the refresh token on logout.
- `/profile` shows authenticated identity, university verification, editable name/bio, private paginated listings/requests, and database-backed counts. Unsupported saved items, reviews, purchase counts, usernames, and department fields are omitted.
- `/post/create` saves real drafts, supports resumption, validates backend constraints, previews edits, uploads directly to presigned object-storage URLs, and submits through the backend moderation flow. Published, pending-review, and rejected outcomes remain distinct.
- Verification codes are shown only when the backend explicitly returns its development code. The backend currently has no email delivery, resend, or password-reset implementation; the UI explains this limitation instead of claiming an email was sent.
- Feed/category loading skeletons, warm empty states, sanitized errors, and retry actions cover network-dependent sections. No marketplace records are mocked or seeded by the frontend.

## Structure

- `src/features/marketplace/`: homepage composition, cards, presentation helpers, and listing detail dialogs.
- `src/features/account/`: registration, login, email verification, profile, and shared account styling.
- `src/features/posting/`: four-step creation, direct uploads, live preview, and moderation outcomes.
- `src/lib/api/`: types matching the backend schemas and the API request helper.
- `src/app/api/market/[...path]/`: narrow backend proxy and session-cookie handling.
- `src/app/providers.tsx`: TanStack Query client.
- `src/app/tokens.css`, `globals.css`, `src/components/ui/`: existing shared visual foundation.
- `assets/`: all four approved reference composites. These are design references, not product photographs.
- `public/images/campus-room.png`: generated decorative hero photograph, never used as a listing image. Provenance and prompt are in `public/images/README.md`.
- `public/fonts/`: local Satoshi font and its supplied Fontshare license.

## Verification

`backend/tests/test_feed_search.py` verifies title/description search, case handling, literal wildcard escaping, filter/pagination totals, published-only visibility, empty results, and input bounds. Fixtures roll back their database changes.

Browser verification covers real API/feed equality, search, categories, type filters, pagination, detail opening/Escape, login errors, authenticated private OFFER/REQUEST draft saving, profile/logout, delayed loading and retry recovery. Layouts are checked at 1440px, 768px, 390px, and 320px.

The account milestone was verified against a separate PostgreSQL database and MinIO bucket using the real application endpoints. Browser checks cover registration/verification, login errors, HttpOnly cookies, access refresh, profile editing, OFFER creation with direct image upload, REQUEST submission returning pending review, backend logout revocation, rejected-post editing/resubmission, saved-draft resumption, and invalid-session recovery. All four routes were checked at desktop, tablet, 390px, and 320px widths. Disposable verification records never enter the normal marketplace database.

`backend/tests/test_account_pages.py` covers private inventory ownership, accurate counts, profile updates, configuration contracts, and input constraints. Run the backend suite against a disposable database; authentication tests commit records.
