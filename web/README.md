# Velvet Seat Booking

CinemaSeat — Movie Ticket Booking Frontend

You are building CinemaSeat, a premium movie-ticket-booking single-page app. Treat this as a real product for a paying cinema chain — the previous pass on this came back looking like a generic admin dashboard, and that's not acceptable this time. Every screen should look like it belongs in a polished consumer app (think the visual confidence of BookMyShow, Fandango, or a boutique cinema chain's app) — not a Bootstrap form.

Design direction (read this first — this is the part that matters most)

Theme: dark, cinematic, premium. Base background should be a near-black charcoal (not pure #000) — something like #0B0B10–#0E0E14 — with subtle layered surfaces (cards a shade lighter, elevated via soft shadow/glow rather than hard borders).

Accent palette: one warm accent (amber/gold, e.g. #D4AF37-ish) for premium cues, CTAs, and selected states; a distinct red/coral for urgency (hold countdown nearing zero, errors); a calm green for "available"/success. Avoid default Tailwind blue/indigo as the primary brand color — it reads generic.

Typography: a confident display weight for headings (movie titles, screen headers, the step indicator) paired with a clean, highly-legible sans for body/UI text (Inter, Geist, or similar). Strong hierarchy — don't let everything sit at the same weight/size.

Depth & atmosphere: subtle gradients, soft glows behind key elements (e.g. a faint amber glow behind the "SCREEN" bar, a soft radial vignette on the seat map), gentle elevation/shadow on cards instead of flat borders everywhere. This should feel like a dim, lit theatre, not a spreadsheet.

Motion: purposeful micro-interactions — seat hover (scale + glow), seat selection (pulse/ring animation), step-indicator transitions, skeleton loaders while API calls are in flight, smooth toast entrances, a radial/circular progress ring for the hold countdown (not just a bare number).

The seat map is the hero screen — it needs to feel tactile and satisfying to use, like picking real seats. Curved "SCREEN" bar with a glow, clear legend (Available / Held / Booked / Premium / Selected), seats as rounded tiles with a distinct look for PREMIUM (richer color, gold border/accent) vs STANDARD.

The confirmation screen should look like an actual ticket — a stub/boarding-pass layout (perforated or dashed-line divider, QR-style placeholder block, booking ref in a monospace or ticket-style font), not a plain success alert.

Consistent spacing scale, consistent corner radii, consistent shadow language across every component — no screen should look like it came from a different app.

Tech stack (non-negotiable)

React SPA — Vite + TypeScript + Tailwind CSS + shadcn/ui

No backend logic — pure frontend, calling a REST API that already exists

Plain fetch, JSON in/out

Base API URL from env var VITE_API_BASE_URL, defaulting to http://localhost:8000/api/v1

Clean, componentized code — separate components per concern (MovieCard, SeatMap, HoldTimer, PaymentStatus, step indicator, toast/error UI, etc.) since this gets handed to an engineer to wire into an existing Dockerized project afterward.

Flow

Persistent step indicator across the whole journey: Browse → Seat Map → Hold Countdown → Pay → Ticket Confirmation

1. Movie Browse

GET {base}/movies Response: array of { id, title, description, duration_minutes, poster_url, showtimes: [{ id, starts_at, price, theatre_id, theatre_name }] }

Movie cards (poster, title, description, duration) with each movie's showtimes rendered as clickable chips (theatre name + local time + price).

2. Seat Map

GET {base}/showtimes/{id}/seats Response: { showtime_id, movie_title, theatre_name, starts_at, price, seats: [{ id, row_label, seat_number, seat_type, status }] }

status is exactly one of AVAILABLE | HELD | BOOKED.

Grid by row_label × seat_number, "SCREEN" indicator bar above it.

AVAILABLE clickable; HELD/BOOKED disabled with clearly distinct visual states.

PREMIUM seat_type visually upgraded vs STANDARD.

Poll this endpoint every 3–5s while the user is on this screen so seats update live as other users hold/release/book.

3. Hold Seat

POST {base}/showtimes/{id}/holds Body: { seat_id, customer_email }

201 → { hold_id, showtime_id, seat_id, status, expires_at, ttl_seconds }

409 → { detail: "Seat is already held or booked" } — show as a toast/inline error, non-fatal, let the user pick another seat.

On success, start a visible countdown to expires_at — make it prominent, shifting toward the urgent accent color as it nears zero, since the seat auto-releases at zero.

4. Pay

POST {base}/pay Body: { hold_id, currency: "BDT" } 202 → { payment_id, booking_ref, status, poll_url }

Disable the pay button on click, show a clear "processing" state.

5. Poll Payment Status

GET {base}/payments/{payment_id} Response: { payment_id, booking_ref, gateway_payment_id, status, amount, currency, booking_confirmed, created_at }

status: PENDING, INITIATING, SUCCEEDED, FAILED, INITIATION_FAILED, SUCCEEDED_NO_HOLD, CONFLICT_REFUND_REQUIRED, REFUNDED

Poll every 1s until status is no longer PENDING/INITIATING.

SUCCEEDED + booking_confirmed: true → ticket-stub-style success screen with booking_ref.

Any other terminal status → clear failure state, status translated to plain language ("Payment failed", "Seat was taken by someone else — refund required", etc.), with a way to start over.

6. OTP (optional, secondary)

POST {base}/otp/send — Body { phone } → 202 { ref, status } POST {base}/otp/verify — Body { ref, code } → { ref, verified, error }

Small standalone card, clearly labeled "demo," visually secondary, does not gate booking.

State / UX requirements

Handle all network/API errors gracefully with visible messages — never a blank screen or silent failure.

Mobile-responsive; the seat grid especially needs to work on small screens (horizontal scroll or scaled grid — your call, but it must stay usable).

No auth, no accounts — customer_email is a plain text input.

Currency symbol: ৳ (Bangladeshi Taka).

Loading states (skeletons, not spinners-only) for every async screen; empty states designed with the same care as populated ones.

This project was built with [Lovable](https://lovable.dev).

**Live app**: https://gilded-hall.lovable.app

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/0512434d-5d6f-44da-8c72-ca007fd7034a).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
