import asyncio

import pytest


@pytest.mark.asyncio
async def test_100_concurrent_holds_exactly_one_succeeds(test_context):
    client = test_context["client"]

    async def attempt(number: int):
        return await client.post(
            "/api/v1/showtimes/1/holds",
            json={"seat_id": 1, "customer_email": f"buyer{number}@example.com"},
        )

    responses = await asyncio.gather(*(attempt(number) for number in range(100)))
    assert sum(response.status_code == 201 for response in responses) == 1
    assert sum(response.status_code == 409 for response in responses) == 99

