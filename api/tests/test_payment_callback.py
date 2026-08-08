import asyncio
import hashlib
import hmac
import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.models import Booking, BookingStatus, Payment, PaymentEvent, PaymentStatus


async def create_pending_payment(client, email: str) -> dict:
    hold_response = await client.post(
        "/api/v1/showtimes/1/holds",
        json={"seat_id": 1, "customer_email": email},
    )
    hold_id = hold_response.json()["hold_id"]
    pay_response = await client.post("/api/v1/pay", json={"hold_id": hold_id, "currency": "BDT"})
    assert pay_response.status_code == 202
    return pay_response.json()


def signed_event(pay_body: dict, *, event_id: str, status: str = "SUCCEEDED") -> tuple[bytes, dict[str, str]]:
    event = {
        "event_id": event_id,
        "payment_id": "pay_gateway_test",
        "booking_ref": pay_body["booking_ref"],
        "status": status,
        "amount": 500,
        "currency": "BDT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    raw = json.dumps(event, separators=(",", ":")).encode()
    signature = hmac.new(b"test-secret", raw, hashlib.sha256).hexdigest()
    return raw, {"Content-Type": "application/json", "X-Signature": signature}


@pytest.mark.asyncio
async def test_duplicate_callback_creates_one_booking_and_one_revenue_transition(test_context):
    client = test_context["client"]
    pay_body = await create_pending_payment(client, "buyer@example.com")
    raw, headers = signed_event(pay_body, event_id="evt_duplicate_test")

    first = await client.post("/api/v1/payments/callback", content=raw, headers=headers)
    duplicate = await client.post("/api/v1/payments/callback", content=raw, headers=headers)
    assert first.status_code == 200
    assert first.json()["result"] == "confirmed"
    assert duplicate.status_code == 200
    assert duplicate.json()["result"] == "duplicate"

    async with test_context["session_factory"]() as db:
        booking_count = await db.scalar(select(func.count()).select_from(Booking))
        event_count = await db.scalar(select(func.count()).select_from(PaymentEvent))
        payment = await db.scalar(select(Payment).where(Payment.booking_ref == pay_body["booking_ref"]))
    assert booking_count == 1
    assert event_count == 1
    assert payment.status == PaymentStatus.SUCCEEDED
    assert payment.revenue_counted is True


@pytest.mark.asyncio
async def test_concurrent_fresh_duplicate_callbacks_are_deduplicated(test_context):
    client = test_context["client"]
    pay_body = await create_pending_payment(client, "concurrent@example.com")
    raw, headers = signed_event(pay_body, event_id="evt_concurrent_fresh")

    responses = await asyncio.gather(
        client.post("/api/v1/payments/callback", content=raw, headers=headers),
        client.post("/api/v1/payments/callback", content=raw, headers=headers),
    )

    assert [response.status_code for response in responses] == [200, 200]
    assert sorted(response.json()["result"] for response in responses) == ["confirmed", "duplicate"]
    async with test_context["session_factory"]() as db:
        booking_count = await db.scalar(select(func.count()).select_from(Booking))
        event_count = await db.scalar(select(func.count()).select_from(PaymentEvent))
        payment = await db.scalar(select(Payment).where(Payment.booking_ref == pay_body["booking_ref"]))
    assert booking_count == 1
    assert event_count == 1
    assert payment.status == PaymentStatus.SUCCEEDED
    assert payment.revenue_counted is True


@pytest.mark.asyncio
async def test_refund_cancels_booking_and_returns_seat_to_available(test_context):
    client = test_context["client"]
    pay_body = await create_pending_payment(client, "refund@example.com")
    success_raw, success_headers = signed_event(pay_body, event_id="evt_success_before_refund")
    refund_raw, refund_headers = signed_event(pay_body, event_id="evt_refund", status="REFUNDED")

    success = await client.post("/api/v1/payments/callback", content=success_raw, headers=success_headers)
    refunded = await client.post("/api/v1/payments/callback", content=refund_raw, headers=refund_headers)

    assert success.json()["result"] == "confirmed"
    assert refunded.json()["result"] == "refunded"
    async with test_context["session_factory"]() as db:
        payment = await db.scalar(select(Payment).where(Payment.booking_ref == pay_body["booking_ref"]))
        booking = await db.scalar(select(Booking).where(Booking.hold_id == payment.hold_id))
    assert payment.status == PaymentStatus.REFUNDED
    assert payment.revenue_counted is False
    assert booking.status == BookingStatus.CANCELLED

    seat_map = await client.get("/api/v1/showtimes/1/seats")
    assert seat_map.json()["seats"][0]["status"] == "AVAILABLE"
    replacement = await client.post(
        "/api/v1/showtimes/1/holds",
        json={"seat_id": 1, "customer_email": "replacement@example.com"},
    )
    assert replacement.status_code == 201


@pytest.mark.asyncio
async def test_invalid_callback_signatures_are_rejected(test_context):
    client = test_context["client"]
    missing = await client.post("/api/v1/payments/callback", content=b"{}")
    wrong = await client.post(
        "/api/v1/payments/callback",
        content=b"{}",
        headers={"X-Signature": "wrong"},
    )
    assert missing.status_code == 401
    assert wrong.status_code == 401
