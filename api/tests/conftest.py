import asyncio
import os
import time
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("HOLD_TTL_SECONDS", "30")

from app.config import Settings, get_settings
from app.db import get_db
from app.main import app
from app.models import Base, Movie, Seat, Showtime, Theatre
from app.payment.router import get_payment_dispatcher
from app.redis_client import get_redis


class AtomicFakeRedis:
    """Small Redis double with atomic NX and real TTL behavior."""

    def __init__(self) -> None:
        self.values: dict[str, tuple[str, float | None]] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.lock = asyncio.Lock()

    def _live_value(self, key: str) -> str | None:
        item = self.values.get(key)
        if item is None:
            return None
        value, deadline = item
        if deadline is not None and deadline <= time.monotonic():
            self.values.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, *, ex: int | None = None, nx: bool = False):
        async with self.lock:
            current = self._live_value(key)
            if nx and current is not None:
                return None
            deadline = time.monotonic() + ex if ex else None
            self.values[key] = (str(value), deadline)
            return True

    async def get(self, key: str) -> str | None:
        async with self.lock:
            return self._live_value(key)

    async def mget(self, keys: list[str]) -> list[str | None]:
        async with self.lock:
            return [self._live_value(key) for key in keys]

    async def eval(self, script: str, _numkeys: int, key: str, owner: str, *args: str) -> int:
        async with self.lock:
            if self._live_value(key) != owner:
                return 0
            if "redis.call('del'" in script:
                self.values.pop(key, None)
                return 1
            ttl = int(args[0])
            self.values[key] = (owner, time.monotonic() + ttl)
            return 1

    async def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.hashes.setdefault(key, {}).update({name: str(value) for name, value in mapping.items()})
        return len(mapping)

    async def expire(self, _key: str, _seconds: int) -> bool:
        return True


@pytest_asyncio.fixture
async def test_context(tmp_path) -> AsyncIterator[dict]:
    database_path = tmp_path / "cinemaseat-test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as db:
        db.add_all(
            [
                Movie(id=1, title="Test Movie", description="Test", duration_minutes=100),
                Theatre(id=1, name="Test Theatre", city="Dhaka"),
                Seat(id=1, theatre_id=1, row_label="A", seat_number=1, seat_type="STANDARD"),
                Showtime(
                    id=1,
                    movie_id=1,
                    theatre_id=1,
                    starts_at=datetime.now(timezone.utc) + timedelta(days=1),
                    price=Decimal("500.00"),
                ),
            ]
        )
        await db.commit()

    fake_redis = AtomicFakeRedis()
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{database_path}",
        redis_url="redis://unused",
        hold_ttl_seconds=1,
        gateway_secret="test-secret",
    )

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    async def override_redis() -> AsyncIterator[AtomicFakeRedis]:
        yield fake_redis

    async def no_dispatch(_payment_id, _gateway_control_headers=None) -> None:
        return None

    def override_dispatcher():
        return no_dispatch

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = override_redis
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_payment_dispatcher] = override_dispatcher

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield {
            "client": client,
            "session_factory": session_factory,
            "redis": fake_redis,
            "settings": settings,
        }

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
def client(test_context):
    return test_context["client"]
