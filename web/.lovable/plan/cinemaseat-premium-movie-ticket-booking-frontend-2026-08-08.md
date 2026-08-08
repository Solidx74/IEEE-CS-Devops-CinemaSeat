# CinemaSeat — Premium Movie Ticket Booking Frontend

A dark, cinematic single-page booking flow: Browse → Seat Map → Hold → Pay → Ticket. Pure frontend against the existing REST API.

## Design system first

- Near-black charcoal base (`#0B0B10`), layered surfaces one shade lighter, elevation via soft shadow/glow instead of hard borders.
- Accents: warm gold (`#D4AF37`) for CTAs, premium cues and selected seats; red/coral for urgency and errors; calm green for available/success.
- Typography: a confident display face for movie titles, screen headers and the step indicator; clean sans for body/UI; monospace for the booking ref.
- Tokens for the gold glow, radial vignette, screen-bar glow, one spacing scale, one radius scale, one shadow language — all defined centrally so no screen drifts.
- Motion: seat hover (scale + glow), selection pulse ring, step transitions, skeleton loaders, toast entrances, circular progress ring for the countdown.

## Screens

1. **Browse** — hero header, movie cards (poster, title, description, duration) with showtimes as clickable gold-outlined chips (theatre · local time · ৳price). Skeleton cards while loading; designed empty state.
2. **Seat Map (hero screen)** — curved glowing SCREEN bar, seats as rounded tiles gridded by row × number, legend (Available / Held / Booked / Premium / Selected), premium seats richer with gold border. Held/Booked disabled and visually distinct. Polls every 4s for live updates. Horizontal scroll with sticky row labels on mobile. Email input + hold CTA in a sticky bottom summary bar.
3. **Hold** — prominent circular countdown ring to `expires_at`, shifting gold → coral as it nears zero; auto-release message at zero. 409 surfaces as a non-fatal toast and returns the user to seat picking.
4. **Pay** — order summary card, pay button disables on click with a processing state.
5. **Payment polling** — 1s polling until terminal; all statuses translated to plain language (e.g. "Seat was taken by someone else — refund required").
6. **Ticket confirmation** — boarding-pass stub: dashed perforation divider, QR-placeholder block, booking ref in ticket-style mono, movie/theatre/seat/time details, gold foil accents.
7. **OTP demo card** — small, visually secondary, labelled "demo", never gates booking.

A persistent step indicator sits above every screen.

## Technical notes

- Vite + TypeScript + Tailwind + shadcn/ui, plain `fetch`, JSON in/out.
- `VITE_API_BASE_URL` with fallback `http://localhost:8000/api/v1`, read through a single `src/lib/api.ts` client with typed request helpers and a shared error shape.
- Types in `src/types/booking.ts` mirroring the API contracts exactly (`AVAILABLE | HELD | BOOKED`, the eight payment statuses).
- Components: `StepIndicator`, `MovieCard`, `ShowtimeChip`, `SeatMap`, `Seat`, `SeatLegend`, `ScreenBar`, `HoldTimer` (ring), `PaymentStatus`, `TicketStub`, `OtpDemoCard`, `SkeletonCard`/`SkeletonSeatMap`, error/empty states.
- Hooks: `useMovies`, `useSeats` (polling), `useHold` (countdown), `usePayment` (polling) — polling intervals cleaned up on unmount/step change.
- Flow state held in one page-level reducer on `/` so the journey is a genuine SPA; sonner toasts for non-fatal errors, inline error panels for fatal ones. No blank screens, no silent failures.
- Currency rendered as ৳ everywhere; no auth, email is a plain input.
- Route metadata (title/description/og) set for the booking page.
