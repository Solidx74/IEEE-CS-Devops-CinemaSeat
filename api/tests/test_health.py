import time

import pytest


@pytest.mark.asyncio
async def test_health_is_fast_and_does_not_probe_gateway(test_context):
    started = time.monotonic()
    response = await test_context["client"].get("/health")
    elapsed = time.monotonic() - started
    assert response.status_code == 200
    assert elapsed < 1
    assert response.json()["status"] == "ok"
