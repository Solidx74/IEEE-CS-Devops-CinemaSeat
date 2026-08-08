import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.booking.service import extend_hold_key, release_hold_key
from app.config import Settings
from app.models import (
    Booking,
    BookingStatus,
    Hold,
    HoldStatus,
    Payment,
    PaymentEvent,
    PaymentStatus,
)


logger = logging.getLogger(__name__)
TERMINAL_PAYMENT_STATUSES = {
    PaymentStatus.SUCCEEDED,
    PaymentStatus.FAILED,
    PaymentStatus.SUCCEEDED_NO_HOLD,
    PaymentStatus.CONFLICT_REFUND_REQUIRED,
    PaymentStatus.REFUNDED,
}
RECOVERABLE_PAYMENT_STATUSES = {
    PaymentStatus.PENDING,
    PaymentStatus.INITIATING,
}


def booking_reference() -> str:
    return f"CS-{uuid.uuid4().hex[:16].upper()}"


def payment_recovery_stale_seconds(settings: Settings) -> float:
    """Wait past the normal bounded charge attempt window before recovery."""
    return max(
        1.0,
        2 * settings.gateway_request_timeout_seconds * settings.gateway_max_attempts,
    )


def payment_needs_recovery(payment: Payment, settings: Settings, *, now: datetime | None = None) -> bool:
    if payment.status not in RECOVERABLE_PAYMENT_STATUSES:
        return False
    updated_at = payment.updated_at or payment.created_at
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(seconds=payment_recovery_stale_seconds(settings))
    return updated_at <= cutoff


async def initiate_gateway_charge(
    payment_id: uuid.UUID,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    gateway_control_headers: dict[str, str] | None = None,
) -> None:
    """Runs after POST /pay has returned. Retries transport failures safely."""
    for attempt in range(1, settings.gateway_max_attempts + 1):
        async with session_factory() as db:
            payment = await db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
            if payment is None or payment.status in TERMINAL_PAYMENT_STATUSES:
                return
            payment.status = PaymentStatus.INITIATING
            payment.initiation_attempts = attempt
            await db.commit()
            body = {
                "amount": float(payment.amount),
                "currency": payment.currency,
                "booking_ref": payment.booking_ref,
                "callback_url": settings.gateway_callback_url,
            }
            idempotency_key = payment.booking_ref

        try:
            timeout = httpx.Timeout(settings.gateway_request_timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout) as client:
                headers = {"Idempotency-Key": idempotency_key}
                if gateway_control_headers:
                    headers.update(gateway_control_headers)
                response = await client.post(
                    f"{settings.gateway_url.rstrip('/')}/charge",
                    json=body,
                    headers=headers,
                )
                response.raise_for_status()
                gateway_body = response.json()
                gateway_payment_id = gateway_body["payment_id"]

            async with session_factory() as db:
                payment = await db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
                if payment is None:
                    return
                if payment.gateway_payment_id is None:
                    payment.gateway_payment_id = gateway_payment_id
                if payment.status not in TERMINAL_PAYMENT_STATUSES:
                    payment.status = PaymentStatus.PENDING
                payment.last_error = None
                await db.commit()
            return
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.warning("gateway charge attempt %s failed for %s: %s", attempt, payment_id, exc)
            if attempt < settings.gateway_max_attempts:
                await asyncio.sleep(min(2 ** (attempt - 1), 4))
                continue
            async with session_factory() as db:
                payment = await db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
                if payment is not None and payment.status not in TERMINAL_PAYMENT_STATUSES and not payment.gateway_payment_id:
                    payment.status = PaymentStatus.INITIATION_FAILED
                    payment.last_error = str(exc)[:1000]
                    await db.commit()


async def recover_stale_payment_dispatches(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=payment_recovery_stale_seconds(settings))
    async with session_factory() as db:
        payment_ids = (
            await db.scalars(
                select(Payment.id).where(
                    Payment.status.in_(RECOVERABLE_PAYMENT_STATUSES),
                    Payment.updated_at <= cutoff,
                )
            )
        ).all()

    if payment_ids:
        logger.warning("recovering %s stale payment dispatch(es)", len(payment_ids))
        await asyncio.gather(
            *(
                initiate_gateway_charge(
                    payment_id,
                    session_factory=session_factory,
                    settings=settings,
                )
                for payment_id in payment_ids
            )
        )
    return len(payment_ids)


async def payment_recovery_loop(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    interval_seconds = min(max(settings.gateway_request_timeout_seconds, 1.0), 5.0)
    while True:
        try:
            await recover_stale_payment_dispatches(session_factory=session_factory, settings=settings)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("stale payment recovery sweep failed")
        await asyncio.sleep(interval_seconds)


async def process_payment_event(
    db: AsyncSession,
    redis: Redis,
    event: dict[str, Any],
    *,
    hold_extension_seconds: int,
) -> str:
    payment = await db.scalar(
        select(Payment).where(Payment.booking_ref == event["booking_ref"]).with_for_update()
    )
    if payment is None:
        await db.rollback()
        return "unknown_booking_ref"

    existing_event = await db.get(PaymentEvent, event["event_id"])
    if existing_event is not None:
        await db.rollback()
        return "duplicate"

    payment_event = PaymentEvent(
        event_id=event["event_id"],
        payment_id=payment.id,
        gateway_payment_id=event["payment_id"],
        status=event["status"],
        payload=event,
    )
    db.add(payment_event)
    if payment.gateway_payment_id is None:
        payment.gateway_payment_id = event["payment_id"]
    elif payment.gateway_payment_id != event["payment_id"]:
        payment.last_error = "Callback payment_id did not match the initiated payment"
        await db.commit()
        return "payment_id_mismatch"

    hold = await db.scalar(select(Hold).where(Hold.id == payment.hold_id).with_for_update())
    status = event["status"].upper()
    should_release = False

    if status == "FAILED":
        if payment.status != PaymentStatus.SUCCEEDED:
            payment.status = PaymentStatus.FAILED
            payment.last_error = "Gateway reported payment failure"
            if hold is not None and hold.status == HoldStatus.HELD:
                hold.status = HoldStatus.RELEASED
                should_release = True
        await db.commit()
        if should_release and hold is not None:
            await release_hold_key(redis, hold.showtime_id, hold.seat_id, hold.id)
        return "failed"

    if status == "REFUNDED":
        if payment.status == PaymentStatus.REFUNDED:
            await db.commit()
            return "already_refunded"
        if payment.status != PaymentStatus.SUCCEEDED:
            payment.last_error = f"Refund callback received while payment was {payment.status.value}"
            await db.commit()
            return "invalid_refund_state"

        booking = await db.scalar(select(Booking).where(Booking.hold_id == payment.hold_id).with_for_update())
        if booking is not None:
            booking.status = BookingStatus.CANCELLED
        payment.status = PaymentStatus.REFUNDED
        payment.revenue_counted = False
        payment.last_error = None
        await db.commit()
        return "refunded"

    if status != "SUCCEEDED":
        await db.commit()
        return "ignored_status"

    if payment.status == PaymentStatus.SUCCEEDED:
        await db.commit()
        return "already_succeeded"

    if hold is None or hold.status != HoldStatus.HELD:
        payment.status = PaymentStatus.SUCCEEDED_NO_HOLD
        payment.last_error = "Payment succeeded after the hold was no longer active; refund required"
        await db.commit()
        return "succeeded_without_hold"

    owns_hold = await extend_hold_key(
        redis,
        hold.showtime_id,
        hold.seat_id,
        hold.id,
        hold_extension_seconds,
    )
    if not owns_hold:
        hold.status = HoldStatus.EXPIRED
        payment.status = PaymentStatus.SUCCEEDED_NO_HOLD
        payment.last_error = "Payment succeeded after Redis hold expiry; refund required"
        await db.commit()
        return "succeeded_without_hold"

    booking = await db.scalar(select(Booking).where(Booking.hold_id == hold.id).with_for_update())
    if booking is None:
        seat_booking = await db.scalar(
            select(Booking)
            .where(
                Booking.showtime_id == hold.showtime_id,
                Booking.seat_id == hold.seat_id,
                Booking.status == BookingStatus.CONFIRMED,
            )
            .with_for_update()
        )
        if seat_booking is not None:
            payment.status = PaymentStatus.CONFLICT_REFUND_REQUIRED
            payment.last_error = "Seat already has a durable booking; refund required"
            await db.commit()
            await release_hold_key(redis, hold.showtime_id, hold.seat_id, hold.id)
            return "booking_conflict"

        booking_values = {
            "id": uuid.uuid4(),
            "reference": payment.booking_ref,
            "hold_id": hold.id,
            "showtime_id": hold.showtime_id,
            "seat_id": hold.seat_id,
            "customer_email": hold.customer_email,
            "amount": payment.amount,
            "status": BookingStatus.CONFIRMED,
        }
        if db.get_bind().dialect.name == "postgresql":
            booking_id = await db.scalar(
                pg_insert(Booking)
                .values(**booking_values)
                .on_conflict_do_nothing(
                    index_elements=[Booking.showtime_id, Booking.seat_id],
                    index_where=Booking.status == BookingStatus.CONFIRMED,
                )
                .returning(Booking.id)
            )
            if booking_id is None:
                payment.status = PaymentStatus.CONFLICT_REFUND_REQUIRED
                payment.last_error = "Seat was booked concurrently; refund required"
                await db.commit()
                await release_hold_key(redis, hold.showtime_id, hold.seat_id, hold.id)
                return "booking_conflict"
        else:
            booking = Booking(**booking_values)
            db.add(booking)

    hold.status = HoldStatus.CONSUMED
    payment.status = PaymentStatus.SUCCEEDED
    payment.revenue_counted = True
    payment.succeeded_at = datetime.now(timezone.utc)
    payment.last_error = None
    await db.commit()
    await release_hold_key(redis, hold.showtime_id, hold.seat_id, hold.id)
    return "confirmed"


async def send_otp_to_gateway(ref: str, phone: str, redis: Redis, settings: Settings) -> None:
    try:
        async with httpx.AsyncClient(timeout=settings.gateway_request_timeout_seconds) as client:
            response = await client.post(
                f"{settings.gateway_url.rstrip('/')}/otp/send",
                json={"phone": phone, "ref": ref, "callback_url": settings.gateway_otp_callback_url},
            )
            response.raise_for_status()
        await redis.hset(f"otp:{ref}", mapping={"status": "PENDING", "phone": phone})
        await redis.expire(f"otp:{ref}", 300)
    except httpx.HTTPError as exc:
        logger.warning("OTP send failed for %s: %s", ref, exc)
        await redis.hset(f"otp:{ref}", mapping={"status": "SEND_FAILED", "phone": phone})
        await redis.expire(f"otp:{ref}", 300)


async def verify_otp_with_gateway(ref: str, code: str, redis: Redis, settings: Settings) -> tuple[bool, str | None]:
    try:
        async with httpx.AsyncClient(timeout=settings.gateway_request_timeout_seconds) as client:
            response = await client.post(
                f"{settings.gateway_url.rstrip('/')}/otp/verify",
                json={"ref": ref, "code": code},
            )
        body = response.json()
        verified = response.is_success and body.get("verified") is True
        error = None if verified else body.get("error", "OTP_VERIFY_FAILED")
        await redis.hset(f"otp:{ref}", mapping={"status": "VERIFIED" if verified else "REJECTED"})
        await redis.expire(f"otp:{ref}", 300)
        return verified, error
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("OTP verify failed for %s: %s", ref, exc)
        return False, "GATEWAY_UNAVAILABLE"
