# RamaiahMart — Product Specification

## 1. Product Overview

RamaiahMart is a private university classifieds and marketplace platform for Ramaiah students.

The core idea is simple:

> A student can post something they have, or post something they need.

The platform is not limited to buying and selling physical products. Students can use it to discover or offer:

- Products for sale
- Products for rent
- Products to borrow
- Bikes and cars
- Tutors and other student services
- Rooms and roommates
- Wanted items
- Other useful campus-related opportunities

The first version is intentionally lightweight. The goal is to validate whether students actually use the platform before introducing payments, auctions, offers, delivery, or other complex marketplace features.

---

## 2. Product Philosophy

### One account, multiple roles

There are no separate buyer and seller accounts.

Every user is a verified student and can:

- Browse
- Buy
- Rent
- Borrow
- Offer something
- Request something
- Start conversations
- Manage their own posts

A user becomes a "seller" only when they create an offer.

### The fundamental abstraction

Every post is either:

- `OFFER` — "I have this."
- `REQUEST` — "I need this."

Examples:

| Type | Example |
|---|---|
| OFFER | Casio FX-991EX for ₹1,200 |
| OFFER | Mountain bike for ₹150/day |
| OFFER | DBMS tutoring for ₹300/hour |
| OFFER | Room available in 3BHK |
| REQUEST | Looking for a calculator |
| REQUEST | Need a bike for 5 days |
| REQUEST | Looking for a DBMS tutor |
| REQUEST | Looking for a roommate |

---

## 3. V1 Goals

The V1 must prove three things:

1. Students are willing to create posts.
2. Students are willing to browse/discover posts.
3. Students are willing to contact each other through the platform.

The primary marketplace loop is:

```text
Student signs in
    ↓
Browses posts
    ↓
Finds something useful
    ↓
Opens post
    ↓
Starts conversation
    ↓
Buyer/requester and poster continue transaction
```

For an offer:

```text
Create offer
    ↓
AI moderation
    ↓
Publish
    ↓
Another student discovers it
    ↓
Conversation
```

For a request:

```text
Create request
    ↓
AI moderation
    ↓
Publish
    ↓
Another student discovers it
    ↓
Conversation
```

---

## 4. Explicit V1 Exclusions

Do NOT implement these in V1:

- Payments
- Escrow
- Auctions
- Bidding
- Offers/negotiation system
- Delivery
- Internal transaction settlement
- Complex recommendation engine
- Automated matching engine
- WhatsApp API
- Separate buyer/seller accounts

Users may share phone numbers in conversation if they choose.

WhatsApp can be considered later as an optional continuation channel, but the initial interaction should happen inside the platform.

---

## 5. Main User Experience

### Home

After login, the user should immediately see posts.

The homepage should not force the user through a large onboarding flow.

Core areas:

- Search
- Recent posts
- Categories
- Offer/request distinction
- Post creation CTA
- Profile access
- Conversations

Primary search examples:

- "calculator"
- "bike"
- "DBMS tutor"
- "roommate"
- "monitor"
- "camera"

---

## 6. Creating a Post

The post creation experience should feel conversational and lightweight rather than like a large enterprise form.

The user chooses:

```text
I HAVE SOMETHING
I NEED SOMETHING
```

Then the system asks for the minimum useful information.

### Required fields

For an OFFER:

- Product/service name
- Short description
- Image
- Price/quote

For a REQUEST:

- What the user needs
- Short description
- Budget/quote where applicable

The system should not require users to fill every possible metadata field.

### Optional fields

Depending on the post:

- Category
- Condition
- Brand
- Location
- Availability
- Price unit
- Rental period
- Contact preferences

AI may infer or suggest metadata such as category and brand.

The user should be able to review generated metadata before publishing where appropriate.

---

## 7. Post Types and Categories

Initial categories should be broad and extensible.

Suggested categories:

- Electronics
- Books & Study
- Vehicles
- Room & Housing
- Services
- Furniture
- Sports
- Fashion
- Events
- Other

The category system must not be hard-coded into frontend components.

Categories should be stored in the database and served by the API.

---

## 8. Post Lifecycle

A post should have a clear lifecycle.

Initial states:

```text
DRAFT
PENDING_REVIEW
PUBLISHED
REJECTED
ARCHIVED
SOLD
RENTED
CLOSED
```

Not every state needs to be exposed to users immediately.

Typical offer flow:

```text
DRAFT
  ↓
PENDING_REVIEW
  ↓
PUBLISHED
  ↓
SOLD / RENTED / ARCHIVED
```

Typical request flow:

```text
DRAFT
  ↓
PENDING_REVIEW
  ↓
PUBLISHED
  ↓
CLOSED / ARCHIVED
```

---

## 9. Authentication and Trust

The platform is intended for one university community.

V1 should support university verification.

Users should have:

- Name
- University email
- Verification state
- Profile image
- Optional bio
- Created date

The UI should visibly communicate verified student status.

Example:

> ✓ Verified Ramaiah Student

The exact university email domain must be configurable rather than scattered throughout the codebase.

---

## 10. Conversations

Conversations are part of V1.

A conversation belongs to:

- One post
- One initiating user
- One post owner

A conversation should preserve context about the post.

Example:

```text
Casio FX-991EX
₹1,200

Buyer:
"Hi, is this still available?"

Seller:
"Yes, it is."
```

The conversation system should support:

- Text messages
- Read state
- Conversation timestamps
- Post reference
- Basic reporting/blocking architecture

Do not implement advanced chat features unless required.

---

## 11. AI Moderation

Every newly submitted post should pass through moderation before becoming publicly visible.

Moderation should evaluate:

### Text

- Prohibited goods/services
- Sexual content
- Harassment
- Fraud/scam indicators
- Spam
- Misleading descriptions
- Obvious abuse

### Images

- Does the image appear to contain an actual product/service context?
- Is it unrelated to the post?
- Is it sexually explicit or abusive?
- Is it obviously a meme/screenshot instead of a useful listing image?
- Does the image conflict with the post description?

The system should not blindly reject any image containing a person. For example, a legitimate bike, clothing, or room listing may contain people.

### Moderation decisions

```text
APPROVE
REVIEW
REJECT
```

Moderation should be designed as a service boundary so the provider/model can change later.

---

## 12. Search

Search is important but should not dominate the first implementation.

The intended future architecture is:

- PostgreSQL = source of truth
- Elasticsearch = search/indexing layer

Initial search requirements:

- Keyword search
- Category filtering
- Offer/request filtering
- Price filtering
- Recency sorting

Semantic/vector search can be added only if real usage demonstrates that it improves discovery.

---

## 13. Image Storage

Images must not be stored directly in PostgreSQL.

Store image metadata in PostgreSQL and image objects in object storage.

Development:

```text
MinIO
```

Production:

```text
Amazon S3
```

The application should use an S3-compatible storage abstraction.

Prefer direct browser uploads using presigned URLs so large image files do not pass through the FastAPI application server.

---

## 14. Analytics

V1 should capture enough data to learn from usage.

Useful events:

- User signup
- Post created
- Post published
- Post viewed
- Search performed
- Category selected
- Conversation started
- Message sent
- Post closed
- Post reported

Primary metrics:

- Active users
- New posts
- Active posts
- Post views
- Conversations started
- Conversation-to-post ratio
- Repeat posters
- Repeat visitors
- Most searched categories
- Unfulfilled requests

Do not build a complicated analytics platform initially. Store only what is useful.

---

## 15. Product Success Criteria

The first milestone is not feature count.

V1 is successful if students:

1. Sign up.
2. Create useful posts.
3. Discover other posts.
4. Start conversations.
5. Return to the platform.

The first product question is:

> "Does a university-specific exchange platform have enough demand and supply to become useful?"

Features should be added based on observed behavior rather than assumptions.

---

## 16. Future Features — Not V1

Potential V2+ features:

- Offers
- Payments
- Auctions
- Rental reservations
- Automated matching between requests and offers
- WhatsApp integration
- Notifications
- Saved searches
- Recommendations
- Seller reputation
- Reviews
- Delivery
- Identity/trust improvements
- Advanced moderation

---

## 17. Account Lifecycle & Data Governance (Phase 5)

### Inactivity Policy
- Non-destructive: Inactivity carries zero penalty.
- After 90 days without meaningful activity, accounts transition to `INACTIVE`.
- Inactive accounts retain all listings, history, and messages without deletion or suspension.
- Meaningful authenticated activity immediately restores the account to `ACTIVE`.

### User-Requested Deletion
- Users can request deletion from profile settings.
- 15-day grace period (`DELETION_PENDING`).
- Logging in or performing qualifying activity during the 15-day window automatically cancels deletion.
- Permanent deletion scrubs relational records and deletes all associated object storage assets.
- Disaster recovery backups follow a rolling 7-day retention schedule, omitting deleted accounts upon subsequent backup synchronization.

