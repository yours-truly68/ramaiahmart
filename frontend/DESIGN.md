# RamaiahMart visual system

The approved images in `frontend/assets/` are the visual source of truth for every future page. This foundation preserves their warm cream ground, near-black geometric type, small orange accents, pastel surfaces, thin edges, generous spacing, and modest corner radii. It serves students browsing between classes on desktop and phone, often in bright ambient light: a light canvas and strong contrast keep the UI readable.

## Reference map — all four images inspected

| Future surface | Approved reference | Principles to carry forward |
| --- | --- | --- |
| Homepage / feed | `assets/RamaiahMart Campus Marketplace.png` | Wide editorial headline beside lifestyle photography; a slim horizontal navigation bar; dominant search; pastel category surfaces; generous image areas and compact metadata. |
| Profile | `assets/RamaiahMart Student Marketplace Profile.png` | Spacious identity header, circular portrait, restrained verification treatment, thin dividers, warm cards and quiet secondary controls. |
| Create / post | `assets/RamaiahMart New Listing Dashboard.png` | Narrow editorial support column, clear central form, subordinate preview; outlined inputs; soft-orange selection, small steps and generous grouping. |
| Login | Left half of `assets/RamaiahMart Student Marketplace Onboarding.png` | Oversized welcome copy, warm photographic setting, compact light form surface, one clear action. |
| Registration | Right half of `assets/RamaiahMart Student Marketplace Onboarding.png` | Asymmetric headline/photo and form composition, short labels, comfortable spacing and a restrained orange focal point. |

These are design references, not a feature specification. Do not import reference identities, emails, statistics, reviews, unrelated branding, logos or product names. Do not infer social login, saved items, ratings, analytics, sidebars or extra onboarding requirements from a picture. Real navigation and interactions must follow the product brief; a still image cannot define behavior. No product pages are built in this milestone.

## Colour

`src/app/tokens.css` is the canonical value source. All core colours have Tailwind aliases, e.g. `bg-background`, `text-foreground`, `border-border`, `bg-accent-soft-orange`, `text-request`.

| Token | Value | Role |
| --- | --- | --- |
| background | `#FAF6EE` | Warm page canvas |
| foreground | `#171714` | Main text, primary controls |
| muted-foreground | `#666159` | Supporting copy and placeholders |
| border | `#E4DED4` | Decorative dividers and card edges |
| card | `#FFFDF9` | Content surfaces |
| accent-orange | `#FF5A1F` | Sparse focal accents and emphasis |
| accent-soft-orange | `#FFE5D3` | Supporting orange surfaces |
| success | `#246039` | Success / verified ink |
| warning | `#805100` | Pending / caution ink |
| destructive | `#A72F2B` | Errors and destructive actions |
| offer | `#98380F` | Offer label ink on peach |
| request | `#274F8E` | Request label ink on blue |

Use corresponding `*-soft` tokens behind semantic status inks. Sage, blue and lilac are supporting surfaces, not new action colours. Labels always carry text; colour is never the only signal. Offer means “I have something,” not a negotiation feature.

The feed's peach Offer and blue Request convention is standardized throughout; the posting reference's green Offer badge is a reference inconsistency. Green is reserved for success/verification/publication.

`accent-ink` is a deeper orange for small text. Bright orange buttons use dark text to maintain contrast, deliberately improving on the screenshots' small white-on-orange labels. Form edges use `input-border`, darker than decorative borders, so controls remain identifiable. Do not place muted gray text on semantic pastel badges: each has its own paired ink.

## Typography and rhythm

- Display: self-hosted Satoshi, 900 weight, fluid 48–96px, 1.02 line height, −0.04em tracking. Use only for meaningful page-level statements.
- Headings: Satoshi 700, fluid 28–40px, 1.15 line height, −0.03em tracking. Smaller headings are 20px with 1.3 line height.
- Body: Inter / system sans, 16px and 1.6 line height. Lead text is 18–22px. Keep long copy around 65 characters wide.
- Metadata: 13px, 1.5 line height; compact, never faint.
- Base spacing: 4px, with 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64 / 96px steps. Tight within groups, generous between them.
- Responsive gutter: 20–72px; content width caps at 1408px. Asymmetric desktop compositions become intentionally ordered single columns on small screens.
- Controls use 8px radii; cards use 12px; avatars are circular. Avoid turning every element into a pill.
- Controls target 48px height, compact buttons no smaller than 44px. Use one 1px edge or a soft offset shadow for elevation.

Satoshi comes directly from Fontshare, unmodified, under the included `public/fonts/FFL.txt`. Use it for this application's rendering, not as a downloadable font offering. It has a local/system fallback; the UI also remains usable if fonts fail.

## Component contracts

All primitives are exported from `@/components/ui`. Native button and input props (including React 19 refs) are forwarded. Styling uses `rm-*` classes so future pages can compose layouts without duplicating control styles.

| Primitive | Contract |
| --- | --- |
| Button | `primary`, `accent`, `secondary`, `ghost`, `destructive`; sizes `sm`, `md`, `lg`. Defaults to `type="button"`. `loading` disables activation and sets `aria-busy`; supply an explicit pending label such as “Saving”. Use native links for navigation. |
| IconButton | Requires `aria-label`. Same variants; square targets. Decorative icon hidden from assistive technology. Use `aria-pressed` for toggles. |
| Input | Requires a persistent `label`. `hint` and `error` connect to the input via generated IDs, preserving caller descriptions. Error sets `aria-invalid`. Validation remains the caller's responsibility. |
| SearchInput | Input with search semantics and a decorative Lucide search icon. No fetching, results, or submit behavior is assumed. |
| Badge | A textual label, not a clickable control. `neutral`, `offer`, `request`, `success`, `warning`, `destructive`. |
| StatusBadge | Presentation of the eight documented post statuses. No lifecycle or authorization logic. Pending review uses warning, published success, rejected destructive; completed/inactive states are neutral. |
| Card | Neutral container, not automatically clickable. `default`, `orange`, `sage`, `blue`, `lilac`; opt-in `elevated`. Add semantic article/section wrappers where appropriate. |
| Avatar | Name, optional image URL, three sizes, initials fallback including load failure. Mark `decorative` when an adjacent name already identifies the person. |
| Divider | Semantic horizontal rule. |
| SectionHeading | `title`, optional `description` and `action`. Defaults to `h2`; supports `h3`. Actions wrap on narrow screens. |
| EmptyState | Explanatory `title` and `description`, optional decorative `icon` and explicit caller-owned `action`. No synthetic success claims. |
| Skeleton | Decorative `line`, `circle`, or `image`. Label the containing region and set `aria-busy`, then remove busy when content resolves. No layout shifting shimmer. |

```tsx
import { Button, Input, Badge, Card, SectionHeading } from "@/components/ui";

<Input label="Title" name="title" required hint="Keep it short and specific." />
<Button type="submit" loading={isSaving}>
  {isSaving ? "Saving" : "Save changes"}
</Button>
<Badge tone="request">Request</Badge>
<Card><SectionHeading as="h3" title="Details" /></Card>
```

## Imagery and future compositions

Use real, approved lifestyle/product photos with natural warm light, clear subjects and uncluttered crops. Cards should leave photographs room to lead; retain `object-fit: cover` and choose each crop deliberately. Reference composites are not production photos and must not be sliced into product assets. Any later illustrative imagery must be sourced separately with appropriate rights and alt text.

Use hand-drawn notes only beside meaningful editorial photography and at most sparingly per surface. Do not add decorative doodles to controls, empty states or every card. None is needed for the component specimen.

Desktop proportions and visual rhythm come from the corresponding reference. Preserve focus order when layouts collapse. Do not infer fixed sidebars or oversized promotional heroes for every task. Avoid dense dashboard chrome, gradients, glass, excessive pills and marketplace-template styling.

## Interaction and accessibility

Native semantics, visible focus rings, descriptive names, 44–56px button targets, linked field errors, explicit status text and reduced-motion support are part of the primitives. Hover effects are limited to colour/edge changes and run only on hover-capable devices. Motion tokens are 160ms with ease-out; only busy controls and loading skeletons animate continuously, and both stop under reduced motion. New dialogs, menus, selectors or complex flows should use an established accessible implementation when actually needed, not speculative custom widgets.

`/design-system` demonstrates local control feedback, a saved-state toggle, a clearable example validation error, disabled/loading buttons, all status labels, identity fallback, surfaces and empty/loading compositions. Its synthetic content is explicitly labelled. It is not a product route or an API feature.
