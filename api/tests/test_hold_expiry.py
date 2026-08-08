import asyncio

import pytest


@pytest.mark.asyncio
async def test_expired_hold_automatically_returns_seat_to_available(test_context):
    client = test_context["client"]
    first = await client.post(
        "/api/v1/showtimes/1/holds",
        json={"seat_id": 1, "customer_email": "first@example.com"},
    )
    assert first.status_code == 201

    held_map = await client.get("/api/v1/showtimes/1/seats")
    assert held_map.json()["seats"][0]["status"] == "HELD"

    await asyncio.sleep(1.1)
    expired_map = await client.get("/api/v1/showtimes/1/seats")
    assert expired_map.json()["seats"][0]["status"] == "AVAILABLE"

    second = await client.post(
        "/api/v1/showtimes/1/holds",
        json={"seat_id": 1, "customer_email": "second@example.com"},
    )
    assert second.status_code == 201

