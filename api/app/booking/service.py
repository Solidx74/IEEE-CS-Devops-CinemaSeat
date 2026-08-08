import uuid
from datetime import datetime, timedelta, timezone

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, BookingStatus, Hold, HoldStatus, Seat, Showtime


RELEASE_IF_OWNER_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""

EXTEND_IF_OWNER_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('expire', KEYS[1], ARGV[2])
end
return 0
"""


class SeatUnavailableError(Exception):
    pass


class InvalidSeatError(Exception):
    pass


def hold_key(showtime_id: int, seat_id: int) -> str:
    return f"seat_hold:{showtime_id}:{seat_id}"


async def release_hold_key(redis: Redis, showtime_id: int, seat_id: int, hold_id: uuid.UUID | str) -> bool:
    result = await redis.eval(RELEASE_IF_OWNER_LUA, 1, hold_key(showtime_id, seat_id), str(hold_id))
    return bool(result)


async def extend_hold_key(
    redis: Redis,
    showtime_id: int,
    seat_id: int,
    hold_id: uuid.UUID | str,
    ttl_seconds: int,
) -> bool:
    result = await redis.eval(
        EXTEND_IF_OWNER_LUA,
        1,
        hold_key(showtime_id, seat_id),
        str(hold_id),
        str(ttl_seconds),
    )
    return bool(result)


async def create_hold(
    db: AsyncSession,
    redis: Redis,
    *,
    showtime_id: int,
    seat_id: int,
    customer_email: str,
    ttl_seconds: int,
) -> Hold:
    row = (
        await db.execute(
            select(Showtime, Seat)
            .join(Seat, Seat.theatre_id == Showtime.theatre_id)
            .where(Showtime.id == showtime_id, Seat.id == seat_id)
        )
    ).one_or_none()
    if row is None:
        raise InvalidSeatError

    already_booked = await db.scalar(
        select(Booking.id).where(
            Booking.showtime_id == showtime_id,
            Booking.seat_id == seat_id,
            Booking.status == BookingStatus.CONFIRMED,
        )
    )
    if already_booked is not None:
        raise SeatUnavailableError

    hold_id = uuid.uuid4()
    claimed = await redis.set(hold_key(showtime_id, seat_id), str(hold_id), ex=ttl_seconds, nx=True)
    if not claimed:
        raise SeatUnavailableError

    now = datetime.now(timezone.utc)
    hold = Hold(
        id=hold_id,
        showtime_id=showtime_id,
        seat_id=seat_id,
        customer_email=customer_email,
        status=HoldStatus.HELD,
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    try:
        db.add(hold)
        await db.commit()
        await db.refresh(hold)
        return hold
    except Exception:
        await db.rollback()
        await release_hold_key(redis, showtime_id, seat_id, hold_id)
        raise

