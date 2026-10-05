# RamaiahMart — Frontend Specification

## 1. Purpose

The frontend is the primary student-facing application.

It should feel like a modern editorial campus product rather than a conventional classifieds website.

The visual reference is:

- warm cream/off-white backgrounds
- large expressive typography
- editorial composition
- strong photography
- asymmetric layouts
- restrained rounded UI
- black/dark typography
- orange accent
- generous whitespace
- minimal chrome

Do not copy any existing website. Use the reference only as visual direction.

---

## 2. Technology

Required:

- Next.js
- TypeScript
- App Router
- Tailwind CSS
- shadcn/ui where useful
- Lucide icons
- TanStack Query for server state

Use Zustand only when persistent client state genuinely requires it.

Avoid unnecessary client-side state.

---

## 3. UX Principle

The application should feel fast and obvious.

The user should immediately understand:

> This is where I find things on campus, and where I can post things I have or need.

Avoid large onboarding flows.

---

## 4. Main Navigation

Primary navigation:

```text
RamaiahMart

Browse
Post
Categories
How it works

Search
Notifications
Profile
```

On smaller screens, navigation can collapse into a mobile navigation pattern.

---

## 5. Home Page

The homepage should combine the editorial reference style with real marketplace functionality.

Hero concept:

> The stuff you need.
> Already on campus.

Supporting text:

> Buy. Sell. Rent. Borrow. Find services. Post what you need.

Primary interaction:

```text
Search bikes, tutors, calculators...
```

Primary post actions:

```text
Buy
Rent
Borrow
Services
Roommate
Wanted
```

Then:

```text
Recently posted
```

with real post cards.

---

## 6. Post Cards

Cards should communicate quickly.

A post card should show:

- primary image
- OFFER/REQUEST badge
- title
- price/quote
- price unit where relevant
- category
- approximate location if provided
- relative timestamp
- favorite/save control if implemented

Example:

```text
FOR SALE

Casio FX-991EX

₹1,200

CSE Block · 2h ago
```

Avoid excessive metadata.

---

## 7. Post Detail

A post detail page should prioritize:

1. Image
2. Title
3. Price/quote
4. Description
5. Poster identity
6. Verification
7. Location/availability
8. Start conversation

Example primary CTA:

```text
Message [Name]
```

Do not use "Buy Now" in V1 because payments do not exist.

---

## 8. Create Post UX

The post flow should feel conversational.

Start:

```text
What are you posting?

[ I HAVE SOMETHING ]
[ I NEED SOMETHING ]
```

Then ask only relevant questions.

For an OFFER:

```text
What are you offering?

Product/service name
Short description
Add photo
Price / quote
```

For a REQUEST:

```text
What are you looking for?

What do you need?
Short description
Add photo (optional)
Budget / quote
```

Mandatory fields must be clearly indicated.

Do not overwhelm the user with optional fields.

---

## 9. Profile

One profile serves all use cases.

Profile should contain:

- name
- university verification
- profile image
- bio
- active posts
- closed posts
- conversations
- account settings

There is no separate buyer dashboard and seller dashboard.

---

## 10. Conversations

Conversation UI should be simple.

Conversation header:

```text
Post title
Poster name
```

Messages appear in a normal chat layout.

The post context should remain accessible from the conversation.

Initial capabilities:

- text
- timestamps
- read state
- basic report/block actions

Do not implement media messaging unless needed.

---

## 11. Search and Browse

Search should be prominent.

Support:

- keyword search
- OFFER/REQUEST filter
- category filter
- price filter
- sort by newest/relevance

The UI should not expose Elasticsearch-specific concepts.

---

## 12. Responsive Design

Desktop should be the primary design canvas because the reference is desktop-oriented.

Mobile must still be fully usable.

Important mobile flows:

- browse
- search
- post creation
- post details
- conversations
- profile

Avoid desktop UI simply squeezed onto a phone.

---

## 13. Accessibility

Use:

- semantic HTML
- keyboard navigation
- visible focus states
- sufficient contrast
- alt text for listing images
- proper form labels
- accessible dialogs
- accessible buttons

Do not use color as the only indication of state.

---

## 14. Loading and Error States

Every network-dependent page needs:

- loading state
- empty state
- error state

Examples:

```text
No posts yet.
Be the first person to post something.
```

Avoid generic "Something went wrong" when a more useful message is possible.

---

## 15. API Integration

The frontend should not contain business logic that belongs to the backend.

Use typed API contracts.

Recommended organization:

```text
src/
├── app/
├── components/
├── features/
│   ├── auth/
│   ├── posts/
│   ├── conversations/
│   └── profile/
├── lib/
│   ├── api/
│   ├── auth/
│   └── utils/
└── types/
```

Use TanStack Query for server state.

---

## 16. Image Upload

The frontend should request a presigned upload URL from the backend.

Flow:

```text
Select image
   ↓
Client validates size/type
   ↓
Request presigned URL
   ↓
Upload directly to storage
   ↓
Notify backend upload completed
   ↓
Attach image to post
```

Do not send large image files through the normal API request.

---

## 17. Visual Rules

### Typography

Use a modern geometric/editorial sans-serif.

Large display typography is encouraged.

Body text should remain highly readable.

### Color

Base:

- warm cream/off-white
- black/dark charcoal text

Accent:

- orange

Use color sparingly.

### Components

Prefer:

- subtle borders
- soft shadows
- rounded corners
- clean iconography
- large image areas
- clear hierarchy

Avoid:

- excessive gradients
- glassmorphism
- excessive pills
- generic dashboard aesthetics
- dense card grids everywhere
- unnecessary animations

---

## 18. Animation

Use motion only when it improves understanding.

Good uses:

- page transitions
- post card hover
- image transitions
- conversational post creation
- subtle navigation feedback

Avoid:

- constant motion
- decorative animation that hurts readability
- heavy animation on mobile

---

## 19. Frontend Non-Goals

Do not build:

- payment UI
- auction UI
- offers UI
- delivery tracking
- seller-specific dashboard
- complex recommendation UI
- advanced analytics dashboards
