import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.booking.service import hold_key
from app.config import Settings, get_settings
from app.db import SessionLocal, get_db
from app.models import Booking, BookingStatus, Hold, HoldStatus, Payment, PaymentStatus, Showtime
from app.payment.schemas import (
    GatewayPaymentEvent,
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    OtpVerifyResponse,
    PayAcceptedResponse,
    PaymentStatusResponse,
    PayRequest,
)
from app.payment.service import (
    booking_reference,
    initiate_gateway_charge,
    payment_needs_recovery,
    process_payment_event,
    send_otp_to_gateway,
    verify_otp_with_gateway,
)
from app.redis_client import get_redis


logger = logging.getLogger(__name__)
router = APIRouter(tags=["payment"])
PaymentDispatcher = Callable[[uuid.UUID, dict[str, str] | None], Awaitable[None]]


def get_payment_dispatcher(settings: Settings = Depends(get_settings)) -> PaymentDispatcher:
    async def dispatch(payment_id: uuid.UUID, gateway_control_headers: dict[str, str] | None = None) -> None:
        await initiate_gateway_charge(
            payment_id,
            session_factory=SessionLocal,
            settings=settings,
            gateway_control_headers=gateway_control_headers,
        )

    return dispatch


def signature_is_valid(raw_body: bytes, signature: str | None, secret: str) -> bool:
    if not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def is_duplicate_event_integrity_error(exc: IntegrityError) -> bool:
    diagnostic = getattr(exc.orig, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    return constraint_name == "payment_events_pkey" or "payment_events.event_id" in str(exc.orig)


async def rollback_callback(db: AsyncSession) -> None:
    try:
        await db.rollback()
    except Exception:
        logger.exception("payment callback rollback failed")


@router.post("/pay", response_model=PayAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def pay(
    body: PayRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
    dispatcher: PaymentDispatcher = Depends(get_payment_dispatcher),
) -> PayAcceptedResponse:
    hold = await db.get(Hold, body.hold_id)
    if hold is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hold not found")

    gateway_control_headers = {
        name: value
        for name in ("X-Mock-Mode", "X-Mock-Force")
        if (value := request.headers.get(name)) is not None
    }
    existing = await db.scalar(select(Payment).where(Payment.hold_id == hold.id))
    if existing is not None:
        if payment_needs_recovery(existing, settings):
            background_tasks.add_task(dispatcher, existing.id, gateway_control_headers or None)
        return PayAcceptedResponse(
            payment_id=existing.id,
            booking_ref=existing.booking_ref,
            status=existing.status.value,
            poll_url=f"/api/v1/payments/{existing.id}",
        )

    now = datetime.now(timezone.utc)
    expires_at = hold.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    redis_owner = await redis.get(hold_key(hold.showtime_id, hold.seat_id))
    if hold.status != HoldStatus.HELD or expires_at <= now or redis_owner != str(hold.id):
        if hold.status == HoldStatus.HELD:
            hold.status = HoldStatus.EXPIRED
            await db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hold has expired")

    showtime = await db.get(Showtime, hold.showtime_id)
    if showtime is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Showtime no longer exists")
    payment = Payment(
        hold_id=hold.id,
        booking_ref=booking_reference(),
        amount=showtime.price,
        currency=body.currency.upper(),
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    try:
        await db.commit()
        await db.refresh(payment)
    except IntegrityError:
        await db.rollback()
        payment = await db.scalar(select(Payment).where(Payment.hold_id == hold.id))
        if payment is None:
            raise

    background_tasks.add_task(dispatcher, payment.id, gateway_control_headers or None)
    return PayAcceptedResponse(
        payment_id=payment.id,
        booking_ref=payment.booking_ref,
        status="ACCEPTED",
        poll_url=f"/api/v1/payments/{payment.id}",
    )


@router.get("/payments/{payment_id}", response_model=PaymentStatusResponse)
async def payment_status(payment_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> PaymentStatusResponse:
    payment = await db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    booking = await db.scalar(
        select(Booking.id).where(
            Booking.hold_id == payment.hold_id,
            Booking.status == BookingStatus.CONFIRMED,
        )
    )
    return PaymentStatusResponse(
        payment_id=payment.id,
        booking_ref=payment.booking_ref,
        gateway_payment_id=payment.gateway_payment_id,
        status=payment.status.value,
        amount=payment.amount,
        currency=payment.currency,
        booking_confirmed=booking is not None,
        created_at=payment.created_at,
    )


@router.post("/payments/callback", status_code=status.HTTP_200_OK)
async def payment_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Acknowledge every delivery, including malformed and duplicate ones."""
    raw = await request.body()
    if not signature_is_valid(raw, request.headers.get("X-Signature"), settings.gateway_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid gateway signature")
    try:
        event_model = GatewayPaymentEvent.model_validate_json(raw)
        event = event_model.model_dump(mode="json")
        result = await process_payment_event(
            db,
            redis,
            event,
            hold_extension_seconds=settings.hold_ttl_seconds,
        )
        return {"received": True, "result": result}
    except ValidationError as exc:
        await rollback_callback(db)
        logger.warning("malformed payment callback ignored: %s", exc)
        return {"received": True, "result": "malformed"}
    except IntegrityError as exc:
        await rollback_callback(db)
        if is_duplicate_event_integrity_error(exc):
            return {"received": True, "result": "duplicate"}
        logger.exception("payment callback integrity failure")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Callback processing temporarily unavailable",
        ) from exc
    except Exception as exc:
        await rollback_callback(db)
        logger.exception("payment callback processing failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Callback processing temporarily unavailable",
        ) from exc


@router.post("/otp/send", response_model=OtpSendResponse, status_code=status.HTTP_202_ACCEPTED)
async def send_otp(
    body: OtpSendRequest,
    background_tasks: BackgroundTasks,
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> OtpSendResponse:
    ref = f"otp_{uuid.uuid4().hex[:16]}"
    await redis.hset(f"otp:{ref}", mapping={"status": "QUEUED", "phone": body.phone})
    await redis.expire(f"otp:{ref}", 300)
    background_tasks.add_task(send_otp_to_gateway, ref, body.phone, redis, settings)
    return OtpSendResponse(ref=ref, status="QUEUED")


@router.post("/otp/verify", response_model=OtpVerifyResponse)
async def verify_otp(
    body: OtpVerifyRequest,
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> OtpVerifyResponse:
    verified, error = await verify_otp_with_gateway(body.ref, body.code, redis, settings)
    return OtpVerifyResponse(ref=body.ref, verified=verified, error=error)


@router.post("/otp/callback", status_code=status.HTTP_200_OK)
async def otp_callback(
    request: Request,
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    raw = await request.body()
    if not signature_is_valid(raw, request.headers.get("X-Signature"), settings.gateway_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid gateway signature")
    try:
        body = await request.json()
        ref = str(body["ref"])
        await redis.hset(f"otp:{ref}", mapping={"status": "DELIVERED"})
        await redis.expire(f"otp:{ref}", 300)
        return {"received": True, "result": "delivered"}
    except Exception:
        return {"received": True, "result": "ignored"}
