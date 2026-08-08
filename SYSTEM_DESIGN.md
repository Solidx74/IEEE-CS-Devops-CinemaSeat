# System Design

This document is the diagram-first companion to [DECISIONS.md](DECISIONS.md). Where DECISIONS.md argues *why*, this document shows *what* — component boundaries, the data model, every state machine, and the exact sequence of calls for the happy path and each documented race condition.

## Contents

- [Component diagram](#component-diagram)
- [Data model](#data-model)
- [State machines](#state-machines)
  - [Hold lifecycle](#hold-lifecycle)
  - [Payment lifecycle](#payment-lifecycle)
  - [Booking lifecycle](#booking-lifecycle)
- [Booking and payment sequence](#booking-and-payment-sequence)
  - [Happy path](#happy-path)
  - [Race: 100 buyers, one seat](#race-100-buyers-one-seat)
  - [Race: duplicate callback delivery](#race-duplicate-callback-delivery)
  - [Race: callback arrives before the charge response](#race-callback-arrives-before-the-charge-response)
  - [Failure: API crash between dispatch and callback](#failure-api-crash-between-dispatch-and-callback)
  - [Failure: hold expires before payment succeeds](#failure-hold-expires-before-payment-succeeds)
- [Request/response shapes](#requestresponse-shapes)

## Component diagram

```mermaid
flowchart TB
    subgraph Client
        Browser[React 19 SPA<br/>TanStack Query + Router]
    end

    subgraph "Web tier — nginx :3000"
        Nginx[Unprivileged nginx<br/>static assets + /api/* proxy]
    end

    subgraph "API tier — FastAPI :8000 (one deployable image)"
        direction TB
        CatalogR[catalog/router.py]
        BookingR[booking/router.py]
        PaymentR[payment/router.py]
        CatalogS[catalog reads]
        BookingS[booking/service.py<br/>Lua-scripted hold ops]
        PaymentS[payment/service.py<br/>dispatch · callback · recovery sweep]
        CatalogR --> CatalogS
        BookingR --> BookingS
        PaymentR --> PaymentS
    end

    subgraph "State"
        PG[(PostgreSQL 16<br/>system of record)]
        Redis[(Redis 7<br/>seat_hold:* leases, TTL)]
    end

    subgraph "External"
        Gateway[Mock payment gateway :9000<br/>charge · OTP · HMAC callbacks]
    end

    Browser -->|same-origin fetch| Nginx
    Nginx -->|proxy /api/*| CatalogR
    Nginx --> BookingR
    Nginx --> PaymentR

    CatalogS --> PG
    BookingS --> PG
    BookingS -->|SET NX EX / Lua release+extend| Redis
    PaymentS --> PG
    PaymentS -->|extend/release lease| Redis
    PaymentS -->|POST /charge, Idempotency-Key| Gateway
    Gateway -->|HMAC-signed POST /payments/callback| PaymentR
```

**Ownership boundaries** (also see [ADR-002](DECISIONS.md#adr-002-keep-one-modular-fastapi-deployment)):

| Module | Owns | Never touches |
|---|---|---|
| `catalog` | Movies, showtimes, live seat-map composition | Redis writes, gateway calls |
| `booking` | Hold creation, Lua-scripted release/extend, `hold_key()` naming | Payment or gateway state |
| `payment` | Charge dispatch, callback verification/dedup, recovery sweep, OTP, booking creation on success | Direct seat-map reads (delegates to catalog's composition rule) |

## Data model

```mermaid
erDiagram
    MOVIE ||--o{ SHOWTIME : screens
    THEATRE ||--o{ SHOWTIME : hosts
    THEATRE ||--o{ SEAT : contains
    SHOWTIME ||--o{ HOLD : "leased for"
    SEAT ||--o{ HOLD : "leased for"
    HOLD ||--o| PAYMENT : "pays for"
    HOLD ||--o| BOOKING : "confirms into"
    PAYMENT ||--o{ PAYMENT_EVENT : "receives"

    MOVIE {
        int id PK
        string title
        int duration_minutes
    }
    THEATRE {
        int id PK
        string name
        string city
    }
    SEAT {
        int id PK
        int theatre_id FK
        string row_label
        int seat_number
        string seat_type
    }
    SHOWTIME {
        int id PK
        int movie_id FK
        int theatre_id FK
        datetime starts_at
        numeric price
    }
    HOLD {
        uuid id PK
        int showtime_id FK
        int seat_id FK
        string customer_email
        enum status "HELD/CONSUMED/RELEASED/EXPIRED"
        datetime expires_at
    }
    PAYMENT {
        uuid id PK
        uuid hold_id FK "unique"
        string booking_ref UK "idempotency key"
        string gateway_payment_id UK
        numeric amount
        enum status "8 states, see below"
        int initiation_attempts
        bool revenue_counted
    }
    PAYMENT_EVENT {
        string event_id PK "gateway-assigned, dedup key"
        uuid payment_id FK
        string gateway_payment_id
        string status
        json payload
    }
    BOOKING {
        uuid id PK
        string reference UK
        uuid hold_id FK "unique"
        int showtime_id FK
        int seat_id FK
        enum status "CONFIRMED/CANCELLED"
    }
```

**Constraints that do the actual correctness work** (not just documentation — enforced in `api/app/models.py`):

- `bookings`: a **partial unique index** on `(showtime_id, seat_id) WHERE status = 'CONFIRMED'` — the final no-oversell barrier.
- `bookings.hold_id` and `payments.hold_id`: unique — one payment and one booking per hold, ever.
- `payment_events.event_id`: primary key, gateway-assigned — the durable callback deduplication key.
- `holds`: `CHECK (expires_at > created_at)`.

## State machines

### Hold lifecycle

```mermaid
stateDiagram-v2
    [*] --> HELD: SET seat_hold:* NX EX ttl<br/>succeeds
    HELD --> CONSUMED: payment callback SUCCEEDED,<br/>booking created
    HELD --> RELEASED: payment callback FAILED
    HELD --> EXPIRED: Redis TTL elapses<br/>(lease lost, no reconciler writes this yet)
    CONSUMED --> [*]
    RELEASED --> [*]
    EXPIRED --> [*]
```

The Redis key is authoritative for whether a hold is *currently* live; the PostgreSQL `holds.status` column is the audit trail. These can disagree briefly — see [ADR-001](DECISIONS.md#adr-001-use-redis-leases-with-postgresql-as-the-durable-booking-backstop) and [Known limitations](README.md#known-limitations).

### Payment lifecycle

```mermaid
stateDiagram-v2
    [*] --> PENDING: POST /pay commits intent
    PENDING --> INITIATING: background dispatch begins attempt
    INITIATING --> PENDING: /charge transport succeeds,<br/>awaiting terminal callback
    INITIATING --> INITIATING: transport failure,<br/>bounded retry (backoff 1/2/4s)
    INITIATING --> INITIATION_FAILED: attempts exhausted,<br/>no gateway_payment_id ever recorded
    PENDING --> SUCCEEDED: callback SUCCEEDED,<br/>hold live, booking created
    INITIATING --> SUCCEEDED: callback SUCCEEDED<br/>(can race ahead of charge response)
    PENDING --> FAILED: callback FAILED
    INITIATING --> FAILED: callback FAILED
    PENDING --> SUCCEEDED_NO_HOLD: callback SUCCEEDED,<br/>hold gone/expired
    INITIATING --> SUCCEEDED_NO_HOLD: callback SUCCEEDED,<br/>hold gone/expired
    PENDING --> CONFLICT_REFUND_REQUIRED: callback SUCCEEDED,<br/>seat won by another CONFIRMED booking
    SUCCEEDED --> REFUNDED: callback REFUNDED
    SUCCEEDED --> [*]
    FAILED --> [*]
    INITIATION_FAILED --> [*]
    SUCCEEDED_NO_HOLD --> [*]
    CONFLICT_REFUND_REQUIRED --> [*]
    REFUNDED --> [*]
```

`SUCCEEDED`, `FAILED`, `SUCCEEDED_NO_HOLD`, `CONFLICT_REFUND_REQUIRED`, and `REFUNDED` are terminal — the recovery sweep only touches `PENDING`/`INITIATING` (`RECOVERABLE_PAYMENT_STATUSES` in `payment/service.py`).

### Booking lifecycle

```mermaid
stateDiagram-v2
    [*] --> CONFIRMED: payment callback SUCCEEDED,<br/>seat won the unique-index race
    CONFIRMED --> CANCELLED: payment callback REFUNDED
    CANCELLED --> [*]
    CONFIRMED --> [*]
```

Because the uniqueness index is scoped to `status = 'CONFIRMED'`, a `CANCELLED` row no longer blocks a fresh hold/booking for the same `(showtime_id, seat_id)`.

## Booking and payment sequence

### Happy path

```mermaid
sequenceDiagram
    autonumber
    participant U as Browser
    participant API as FastAPI
    participant R as Redis
    participant PG as PostgreSQL
    participant GW as Mock gateway

    U->>API: POST /showtimes/{id}/holds
    API->>R: SET seat_hold:{st}:{seat} hold_id NX EX ttl
    R-->>API: OK (won the race)
    API->>PG: INSERT holds (status=HELD)
    API-->>U: 201 {hold_id, expires_at, ttl_seconds}

    U->>API: POST /pay {hold_id}
    API->>PG: INSERT payments (status=PENDING, booking_ref)
    API-->>U: 202 {payment_id, booking_ref, poll_url}
    API-->>API: background: initiate_gateway_charge()

    API->>GW: POST /charge (Idempotency-Key: booking_ref)
    GW-->>API: 200 {payment_id: gw_id}
    API->>PG: UPDATE payments SET gateway_payment_id, status=PENDING

    loop every 1s
        U->>API: GET /payments/{payment_id}
        API-->>U: {status: "PENDING"}
    end

    GW->>API: POST /payments/callback (X-Signature, status=SUCCEEDED)
    API->>API: verify HMAC-SHA256 over raw body
    API->>PG: SELECT ... FOR UPDATE payments WHERE booking_ref
    API->>PG: INSERT payment_events (event_id PK)
    API->>R: EXTEND_IF_OWNER_LUA (confirm lease still owned)
    R-->>API: 1 (still owner)
    API->>PG: INSERT booking (status=CONFIRMED), UPDATE hold=CONSUMED,<br/>payment=SUCCEEDED, revenue_counted=true
    API->>PG: COMMIT
    API->>R: RELEASE_IF_OWNER_LUA (free the key early)
    API-->>GW: 200

    U->>API: GET /payments/{payment_id}
    API-->>U: {status: "SUCCEEDED", booking_confirmed: true}
```

### Race: 100 buyers, one seat

```mermaid
sequenceDiagram
    autonumber
    participant B1 as Buyer 1
    participant Bn as Buyers 2..100
    participant API as FastAPI
    participant R as Redis

    par All 100 requests arrive concurrently
        B1->>API: POST /holds {seat 42}
        Bn->>API: POST /holds {seat 42}  (x99)
    end
    API->>R: SET seat_hold:{st}:42 ... NX EX  (x100, arrive at Redis serially)
    R-->>API: OK for exactly one caller
    R-->>API: nil for the other 99
    API-->>B1: 201 Created
    API-->>Bn: 409 Conflict  (x99)
```

`SET ... NX` is atomic at the Redis single-thread execution layer, so exactly one of 100 concurrent `POST /holds` wins regardless of arrival order. Measured: 1×`201`, 99×`409`, 0 oversells, 688 ms burst — see [loadtest/scenario_a.sh](loadtest/scenario_a.sh).

### Race: duplicate callback delivery

```mermaid
sequenceDiagram
    autonumber
    participant GW as Mock gateway
    participant API as FastAPI
    participant PG as PostgreSQL

    par Same event delivered twice, concurrently
        GW->>API: POST /payments/callback (event_id=E1)
        GW->>API: POST /payments/callback (event_id=E1)
    end
    API->>PG: SELECT payment FOR UPDATE WHERE booking_ref  (both requests block/serialize here)
    API->>PG: INSERT payment_events (event_id=E1)  — first caller wins
    PG-->>API: success (first) / unique-violation (second)
    API->>PG: apply booking + payment transition  (first only)
    API->>PG: COMMIT (first) / ROLLBACK, return "duplicate" (second)
    API-->>GW: 200 (first: confirmed)
    API-->>GW: 200 (second: no-op, already applied)
```

The row lock on `payments` plus the `event_id` primary key make the database — not an application-level check — the single source of truth for "have I seen this event." Measured: 100 concurrent replays of an existing event, 100/100 `HTTP 200`, p95 0.563 s against a 5 s gateway timeout — see [loadtest/callback_latency.sh](loadtest/callback_latency.sh).

### Race: callback arrives before the charge response

```mermaid
sequenceDiagram
    autonumber
    participant API as FastAPI
    participant GW as Mock gateway

    API->>GW: POST /charge (Idempotency-Key: booking_ref)
    Note over GW: Gateway processes the charge<br/>and fires the callback immediately
    GW->>API: POST /payments/callback (booking_ref, SUCCEEDED)
    API->>API: locates payment by booking_ref (not gateway_payment_id)
    API->>API: applies SUCCEEDED transition, creates booking
    API-->>GW: 200
    GW-->>API: 200 {payment_id: gw_id}  (charge response arrives after)
    API->>API: gateway_payment_id was unset — now recorded;<br/>status already terminal, left untouched
```

Because the callback keys off the stable `booking_ref` set at intent-creation time — not the gateway's `payment_id`, which only exists after `/charge` returns — the order of these two responses does not matter. See [ADR-003](DECISIONS.md#adr-003-persist-payment-intent-before-asynchronous-gateway-dispatch).

### Failure: API crash between dispatch and callback

```mermaid
sequenceDiagram
    autonumber
    participant API as FastAPI (instance dies)
    participant GW as Mock gateway
    participant API2 as FastAPI (restarted)
    participant PG as PostgreSQL

    API->>GW: POST /charge
    Note over API: Process crashes before<br/>recording gateway_payment_id
    Note over API2: New instance starts;<br/>payment_recovery_loop() begins
    loop every gateway_request_timeout_seconds..5s
        API2->>PG: SELECT payments WHERE status IN (PENDING, INITIATING)<br/>AND updated_at <= now - stale_window
    end
    PG-->>API2: stale payment found
    API2->>GW: POST /charge (same Idempotency-Key: booking_ref)
    GW-->>API2: 200 (idempotent — original or fresh charge)
    API2->>PG: UPDATE payments SET gateway_payment_id, status=PENDING
```

`payment_recovery_stale_seconds()` waits `2 × timeout × max_attempts` past the normal bounded-retry window before treating a payment as abandoned, so a slow-but-alive dispatch is not double-charged under a differing idempotency key.

### Failure: hold expires before payment succeeds

```mermaid
sequenceDiagram
    autonumber
    participant API as FastAPI
    participant R as Redis
    participant PG as PostgreSQL
    participant GW as Mock gateway

    Note over R: TTL elapses — seat_hold:* key<br/>is deleted by Redis natively
    Note over PG: holds.status row still says HELD<br/>(stale until touched)
    GW->>API: POST /payments/callback (SUCCEEDED)
    API->>PG: SELECT hold FOR UPDATE
    API->>R: EXTEND_IF_OWNER_LUA
    R-->>API: 0 (key absent — lost ownership)
    API->>PG: UPDATE hold.status=EXPIRED,<br/>payment.status=SUCCEEDED_NO_HOLD
    API-->>GW: 200
```

Money arrived, but the seat was never durably reserved for this buyer — `SUCCEEDED_NO_HOLD` is recorded for operator-driven refund rather than silently either dropping the payment or oversell-confirming the seat. See [Payment outcomes](README.md#payment-outcomes).

## Request/response shapes

Full request/response schemas are generated live from the FastAPI application and browsable at `/docs` once the stack is running (see [Quick start](README.md#quick-start)). The [Minimal API walkthrough](README.md#api-reference) in the README covers the three calls needed to exercise a full booking by hand.

---

Back to [README.md](README.md) · Rationale in [DECISIONS.md](DECISIONS.md) · Gateway mapping in [GATEWAY_RESILIENCE.md](GATEWAY_RESILIENCE.md)
