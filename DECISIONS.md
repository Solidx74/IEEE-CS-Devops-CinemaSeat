# Architecture Decision Records

This document records the decisions behind CinemaSeat's correctness model. It explains what was chosen, why it fits the current workload, where the design can fail safely, and what should replace it when the system grows.

Each entry follows a fixed shape — **Context → Decision → Why/Consequences → Alternatives considered → Revisit when** — so a decision can be audited on its own without reading the whole document.

The guiding priorities, in order, are:

1. never confirm the same seat twice;
2. make retries and duplicate delivery safe;
3. return abandoned inventory automatically;
4. keep the demonstration reproducible with one Compose command; and
5. expose limitations instead of hiding them behind optimistic status names.

See also: [README.md](README.md) for the product-level overview, [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) for diagrams of the components and flows these decisions produce, and [GATEWAY_RESILIENCE.md](GATEWAY_RESILIENCE.md) for the gateway-specific failure mapping.

## Decision index

| ID | Decision | Status |
|---|---|---|
| [ADR-001](#adr-001-use-redis-leases-with-postgresql-as-the-durable-booking-backstop) | Use Redis leases with PostgreSQL as the durable booking backstop | Accepted |
| [ADR-002](#adr-002-keep-one-modular-fastapi-deployment) | Keep one modular FastAPI deployment | Accepted |
| [ADR-003](#adr-003-persist-payment-intent-before-asynchronous-gateway-dispatch) | Persist payment intent before asynchronous gateway dispatch | Accepted |
| [ADR-004](#adr-004-authenticate-serialize-and-deduplicate-gateway-callbacks) | Authenticate, serialize, and deduplicate gateway callbacks | Accepted |
| [ADR-005](#adr-005-keep-otp-separate-from-booking-authorization) | Keep OTP separate from booking authorization | Accepted |
| [ADR-006](#adr-006-cancel-bookings-on-refund-and-make-seats-sellable-again) | Cancel bookings on refund and make seats sellable again | Accepted |
| [ADR-007](#adr-007-serve-the-spa-and-api-through-one-browser-origin) | Serve the SPA and API through one browser origin | Accepted |
| [ADR-008](#adr-008-define-health-as-liveness-not-dependency-readiness) | Define `/health` as liveness, not dependency readiness | Accepted |

All decisions reflect the implementation as of 8 August 2026.

---

## ADR-001: Use Redis leases with PostgreSQL as the durable booking backstop

**Status:** Accepted

### Context

A popular showtime can send many buyers to the same seat in one burst. Holding a PostgreSQL transaction open for the entire checkout would serialize contenders, consume connections, and couple database-lock duration to a human payment flow. The system also needs abandoned inventory to return without a cleanup request.

### Decision

Represent a live hold with this Redis operation:

```text
SET seat_hold:{showtime_id}:{seat_id} {hold_id} NX EX {ttl_seconds}
```

`NX` chooses one winner atomically, `EX` makes the claim a lease, and the UUID value proves ownership. Extension and deletion run through Lua scripts that mutate the key only when its value still matches that hold ID.

PostgreSQL remains the durable authority for completed business state:

- a partial unique index allows at most one `CONFIRMED` booking for `(showtime_id, seat_id)`;
- `payments.hold_id` and `bookings.hold_id` are unique;
- the payment callback locks the payment and hold rows while completing a booking.

Live seat-map status is intentionally composed from both stores:

```text
BOOKED   if PostgreSQL has a CONFIRMED booking
HELD     else if Redis has a live lease
AVAILABLE otherwise
```

### Why

- Contenders resolve with one constant-time Redis operation rather than waiting on a long database transaction.
- Lease expiry returns abandoned inventory automatically.
- Ownership tokens prevent a stale process from deleting or extending a newer buyer's hold.
- The PostgreSQL index is the final no-oversell barrier if an unusual cross-store race reaches booking creation.

### Failure behavior

| Failure | Result |
|---|---|
| Redis claim succeeds, PostgreSQL hold insert fails | The API attempts owner-checked release; otherwise TTL eventually frees the seat |
| PostgreSQL hold row remains `HELD` after Redis expiry | The live seat map shows `AVAILABLE`; the historical row is stale but does not block resale |
| Payment success arrives after the lease is gone | Payment becomes `SUCCEEDED_NO_HOLD`; no booking is created |
| Another confirmed booking wins an exceptional race | The unique index wins; payment becomes `CONFLICT_REFUND_REQUIRED` |
| Redis release after booking commit fails | PostgreSQL still reports `BOOKED`; the redundant lease expires later |

The bias is deliberate: uncertainty may briefly under-sell a seat, but it must not oversell one.

### Consequences

- Redis is a correctness-relevant stateful dependency, not merely a cache.
- Redis and PostgreSQL cannot commit atomically. The design relies on compensation, expiry, and a durable database constraint rather than pretending to have a distributed transaction.
- The database `expires_at` is useful audit metadata, but Redis TTL is authoritative for current hold ownership.
- A reconciliation job is still needed to label abandoned hold rows `EXPIRED` for clean reporting.

### Alternatives considered

- **PostgreSQL row lock for the checkout duration:** simpler storage topology, but poor connection usage and unacceptable human-length transactions.
- **PostgreSQL claim table with short transactions:** viable, but requires a dependable expiry/reaper mechanism and adds contention at the database tier.
- **Redis only:** fast, but insufficient as the final durable no-oversell guarantee.

### Revisit when

The system needs multi-region inventory, Redis failover with stricter consistency semantics, or an auditable reservation ledger. At that point, consider partitioned inventory ownership or a database-backed reservation service with explicit fencing tokens.

---

## ADR-002: Keep one modular FastAPI deployment

**Status:** Accepted

### Context

Catalog reads, holds, payments, and booking creation have different responsibilities, but the critical transitions share models and a database transaction boundary. Independent services would introduce network failure, schema coordination, and distributed consistency before there is evidence that separate scaling is needed.

### Decision

Deploy one FastAPI application with internal modules:

- `catalog` owns movies, showtimes, and live seat-map reads;
- `booking` owns lease acquisition and booking lookup;
- `payment` owns charge dispatch, callback processing, recovery, refund transitions, and OTP integration.

Each module has its own router, schemas, and service code. They share SQLAlchemy models, one Alembic history, and one deployable API image.

### Consequences

- Booking creation and payment transition can remain one local database transaction.
- Local development, CI, and deployment stay small enough for a single Compose stack.
- Modules cannot be deployed or scaled independently.
- In-process background tasks share the API's failure domain.

### Alternatives considered

- **Separate catalog, booking, and payment services:** stronger deployment isolation, but it would require distributed transactions or messaging for the core callback-to-booking path.
- **One undifferentiated application module:** fewer files, but weaker ownership boundaries and harder evolution.

### Revisit when

Measured traffic, team ownership, or release cadence shows that a module needs independent scaling or deployment. Preserve the current idempotency and transaction semantics before extracting it.

---

## ADR-003: Persist payment intent before asynchronous gateway dispatch

**Status:** Accepted

### Context

The mock gateway can delay, fail, time out, retry callbacks, or deliver a callback before its `/charge` response returns. A synchronous `/pay` endpoint would tie client latency to those behaviors and could lose all evidence of an attempt if the API died mid-request.

### Decision

`POST /pay` first commits a local `Payment` with a stable `booking_ref`, then returns `202 Accepted`. Gateway dispatch runs as FastAPI background work and uses that booking reference as its `Idempotency-Key`.

Transport and HTTP failures receive bounded retry attempts. A periodic API-process sweep finds stale `PENDING` or `INITIATING` payments and redispatches them with the same key. A callback locates the local payment by `booking_ref`, so callback-before-response behavior does not depend on the gateway payment ID already being stored.

### Why

- The client receives a durable polling handle quickly.
- Repeated `POST /pay` calls for the same hold return the existing payment instead of creating another charge intent.
- A crash between intent commit and charge completion is recoverable after the API restarts.
- A stable provider idempotency key makes repeated dispatch safe when the gateway honors its contract.

### Consequences

- The API depends on gateway idempotency for safe redelivery.
- Recovery pauses while every API instance is down.
- Multiple API instances can discover the same stale payment; duplicate provider requests are acceptable only because they carry the same key.
- After all configured attempts fail, the payment becomes `INITIATION_FAILED` and requires a new operational policy or customer restart.

### Rejected production shortcut

Marking a payment successful from the `/charge` response was rejected. Only an authenticated callback advances the durable payment/booking state; the charge response merely records the gateway payment ID and returns the intent to `PENDING` if no terminal callback has already won the race.

### Revisit when

Payment delivery becomes production-critical. Replace in-process work with a transactional outbox and a durable worker queue. Keep `booking_ref` as the idempotency key so the external contract survives the migration.

---

## ADR-004: Authenticate, serialize, and deduplicate gateway callbacks

**Status:** Accepted

### Context

Provider callbacks are at-least-once and can be concurrent. An application-level "already seen" query is racy: two processes can both observe absence and both apply the same financial transition.

### Decision

Process a payment callback in this order:

1. verify `X-Signature` as HMAC-SHA256 over the exact raw request body;
2. validate the payload shape;
3. find and lock the payment row by `booking_ref`;
4. insert `event_id` into `payment_events`, where it is the primary key;
5. apply the payment, hold, booking, and `revenue_counted` changes in one database transaction; and
6. release the Redis lease by ownership token after the durable commit.

The global event key makes the database, not a process-local check, the deduplication authority across concurrent workers and restarts. One payment-row lock serializes distinct events for the same payment.

### Acknowledgement policy

| Delivery | Response | Reason |
|---|---|---|
| Missing or invalid HMAC | `401` | Fail closed before parsing or mutation |
| Valid duplicate | `200` | State is already applied; retrying adds no value |
| Valid but malformed payload | `200` | Repeating identical bytes cannot repair it |
| Unknown booking reference | `200` | No local payment can consume it |
| Unsupported status or payment-ID mismatch | `200` | Event is retained for diagnosis; blind retry is not corrective |
| Transient database/internal failure | `503` | The gateway should retry with backoff |

### Consequences

- Callbacks for one payment serialize on a row lock. The measured 100-request replay burst stayed below the gateway timeout, but that is not an unlimited capacity claim.
- `payment_events` is an append-only audit/dedup table and needs retention or archival at scale.
- The current callback trusts the signed provider for event amount and currency; it records them but does not compare them with the local payment intent. Production hardening should reject or quarantine mismatches.
- The state machine assumes sensible provider event ordering. Conflicting out-of-order terminal events need stricter transition rules or operator reconciliation.
- The Boolean `revenue_counted` flag demonstrates idempotent recognition; it is not a substitute for an immutable accounting ledger.

### Alternatives considered

- **Check then insert without a unique key:** rejected because concurrent deliveries race.
- **Acknowledge before durable processing:** lower callback latency, but events can be lost unless a durable webhook inbox exists.
- **Return errors for malformed or unknown events:** creates retry noise for conditions that identical redelivery cannot fix.

### Revisit when

The provider retry window is insufficient or callback volume threatens database latency. Add a durable webhook inbox, acknowledge after ingress commit, and process asynchronously with the same event-ID uniqueness rule.

---

## ADR-005: Keep OTP separate from booking authorization

**Status:** Accepted

### Context

The supplied gateway exposes OTP send and verify operations, including delayed or lost delivery. The booking requirements do not define whose identity is proven, how verification binds to a customer and hold, how resend invalidates earlier references, or what recovery policy applies when delivery disappears.

### Decision

Integrate `/otp/send`, `/otp/verify`, and the signed OTP delivery callback as an explicitly optional demonstration. Do not make OTP a prerequisite for `hold -> pay -> booking`.

### Why

Adding an unbound `otp_ref` field to `/pay` would create the appearance of authorization without a complete security boundary. It would also make the core booking demonstration depend on a deliberately lossy delivery channel.

### Consequences

- The real gateway integration can be demonstrated independently.
- A customer is not blocked from checkout by OTP loss.
- CinemaSeat must not be described as an OTP-protected purchase flow.
- Redis stores short-lived OTP status, but no verified identity is attached to the hold or payment.

### Revisit when

Phone verification becomes a product requirement. Bind a verified, expiring challenge to the authenticated customer and exact hold on the server; enforce one-time consumption; add resend, attempt, and rate limits; and define hold behavior during delivery failure.

---

## ADR-006: Cancel bookings on refund and make seats sellable again

**Status:** Accepted

### Context

An unconditional historical uniqueness rule would strand a seat after refund because the cancelled booking row would still occupy `(showtime_id, seat_id)`. Deleting the booking would discard audit history.

### Decision

For a valid `REFUNDED` event received after `SUCCEEDED`:

- set the payment to `REFUNDED`;
- set `revenue_counted` to `false`;
- retain the booking but change it from `CONFIRMED` to `CANCELLED`; and
- do not recreate a Redis lease.

Booking uniqueness applies only to rows whose status is `CONFIRMED`, so a later buyer can create a new hold and confirmed booking for the same seat.

### Consequences

- The original booking remains available for audit.
- The live seat map returns the seat to `AVAILABLE` immediately after commit.
- A new purchase gets a new hold, payment, and booking history rather than reviving the old records.
- `revenue_counted` is reversed exactly for the demonstrated lifecycle, but automatic gateway refund initiation and a full financial ledger remain out of scope.

### Alternatives considered

- **Delete the booking:** rejected because it destroys history.
- **Keep unconditional seat uniqueness:** rejected because a refunded seat could never be confirmed again.
- **Recreate a Redis hold after refund:** rejected because no buyer owns that lease.

---

## ADR-007: Serve the SPA and API through one browser origin

**Status:** Accepted

### Context

The Vite API base URL is compiled into the browser bundle. Requiring browser CORS configuration for every deployment would add avoidable environment-specific behavior.

### Decision

The production-style web image serves static assets from unprivileged nginx on port 3000 and proxies `/api/*` to the API container. Compose builds the frontend with `VITE_API_BASE_URL=/api/v1`.

Direct Vite development keeps a source fallback of `http://localhost:8000/api/v1`. It must run on port 3000 to match FastAPI's current `http://localhost:3000` development CORS allowlist.

### Consequences

- The normal Compose browser path is same-origin and needs no broad CORS policy.
- API topology stays out of the browser bundle.
- Changing `VITE_API_BASE_URL` requires rebuilding the frontend.
- Deployments that expose the API and web app on different origins must explicitly configure a safe CORS policy; the current API does not offer an environment-driven production allowlist.

---

## ADR-008: Define `/health` as liveness, not dependency readiness

**Status:** Accepted

### Context

If the API health check synchronously probes PostgreSQL, Redis, or the gateway, one dependency outage can make the orchestrator restart an otherwise healthy process repeatedly. That does not repair the dependency and can amplify the incident.

### Decision

`GET /health` reports only that the FastAPI process can answer promptly. It deliberately does not call the database, Redis, or gateway.

### Consequences

- A gateway outage does not trigger an API restart storm.
- Compose can use the endpoint as a liveness signal.
- `200 OK` does not mean the application can currently hold a seat or complete payment.
- Production needs separate readiness and dependency telemetry before routing traffic or declaring the service healthy end to end.

### Revisit when

The deployment platform supports distinct startup, liveness, and readiness probes. Keep this lightweight liveness endpoint and add a bounded readiness endpoint with explicit dependency semantics.

---

## Deferred decisions and explicit non-goals

The current implementation intentionally does not settle these production concerns:

- authentication, customer identity, and authorization;
- rate limiting, abuse prevention, and OTP attempt policy;
- a transactional payment outbox and dedicated worker;
- a durable webhook ingress queue;
- automatic refund API calls and operator tooling;
- an immutable revenue/accounting ledger;
- hold-history reconciliation and retention policies;
- multi-region ownership and disaster-recovery guarantees;
- production metrics, tracing, alerting, and capacity targets; and
- separate readiness/startup probes.

These are not hidden assumptions. They are the next decisions to make when CinemaSeat moves beyond a concurrency-focused demonstration.

---

Back to [README.md](README.md) · Diagrams in [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) · Gateway mapping in [GATEWAY_RESILIENCE.md](GATEWAY_RESILIENCE.md)
