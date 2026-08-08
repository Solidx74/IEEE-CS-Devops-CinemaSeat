from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.booking.schemas import BookingResponse, CreateHoldRequest, HoldResponse
from app.booking.service import InvalidSeatError, SeatUnavailableError, create_hold
from app.config import Settings, get_settings
from app.db import get_db
from app.models import Booking
from app.redis_client import get_redis


router = APIRouter(tags=["booking"])


@router.post("/showtimes/{showtime_id}/holds", response_model=HoldResponse, status_code=status.HTTP_201_CREATED)
async def hold_seat(
    showtime_id: int,
    body: CreateHoldRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> HoldResponse:
    try:
        hold = await create_hold(
            db,
            redis,
            showtime_id=showtime_id,
            seat_id=body.seat_id,
            customer_email=body.customer_email,
            ttl_seconds=settings.hold_ttl_seconds,
        )
    except InvalidSeatError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Showtime or seat not found") from None
    except SeatUnavailableError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seat is already held or booked") from None

    return HoldResponse(
        hold_id=hold.id,
        showtime_id=hold.showtime_id,
        seat_id=hold.seat_id,
        status=hold.status.value,
        expires_at=hold.expires_at,
        ttl_seconds=settings.hold_ttl_seconds,
    )


@router.get("/bookings/{reference}", response_model=BookingResponse)
async def get_booking(reference: str, db: AsyncSession = Depends(get_db)) -> BookingResponse:
    booking = await db.scalar(select(Booking).where(Booking.reference == reference))
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return BookingResponse.model_validate(booking)

