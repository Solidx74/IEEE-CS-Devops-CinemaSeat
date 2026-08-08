from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.booking.service import hold_key
from app.catalog.schemas import MovieSummary, SeatMapItem, SeatMapResponse, ShowtimeSummary
from app.db import get_db
from app.models import Booking, BookingStatus, Movie, Seat, Showtime, Theatre
from app.redis_client import get_redis


router = APIRouter(tags=["catalog"])


@router.get("/movies", response_model=list[MovieSummary])
async def list_movies(db: AsyncSession = Depends(get_db)) -> list[MovieSummary]:
    movies = (await db.scalars(select(Movie).order_by(Movie.title))).all()
    rows = (
        await db.execute(
            select(Showtime, Theatre)
            .join(Theatre, Theatre.id == Showtime.theatre_id)
            .order_by(Showtime.starts_at)
        )
    ).all()
    by_movie: dict[int, list[ShowtimeSummary]] = {}
    for showtime, theatre in rows:
        by_movie.setdefault(showtime.movie_id, []).append(
            ShowtimeSummary(
                id=showtime.id,
                starts_at=showtime.starts_at,
                price=showtime.price,
                theatre_id=theatre.id,
                theatre_name=theatre.name,
            )
        )
    return [
        MovieSummary(
            id=movie.id,
            title=movie.title,
            description=movie.description,
            duration_minutes=movie.duration_minutes,
            poster_url=movie.poster_url,
            showtimes=by_movie.get(movie.id, []),
        )
        for movie in movies
    ]


@router.get("/movies/{movie_id}/showtimes", response_model=list[ShowtimeSummary])
async def list_movie_showtimes(movie_id: int, db: AsyncSession = Depends(get_db)) -> list[ShowtimeSummary]:
    if await db.get(Movie, movie_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    rows = (
        await db.execute(
            select(Showtime, Theatre)
            .join(Theatre, Theatre.id == Showtime.theatre_id)
            .where(Showtime.movie_id == movie_id)
            .order_by(Showtime.starts_at)
        )
    ).all()
    return [
        ShowtimeSummary(
            id=showtime.id,
            starts_at=showtime.starts_at,
            price=showtime.price,
            theatre_id=theatre.id,
            theatre_name=theatre.name,
        )
        for showtime, theatre in rows
    ]


@router.get("/showtimes/{showtime_id}/seats", response_model=SeatMapResponse)
async def get_seat_map(
    showtime_id: int,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> SeatMapResponse:
    row = (
        await db.execute(
            select(Showtime, Movie, Theatre)
            .join(Movie, Movie.id == Showtime.movie_id)
            .join(Theatre, Theatre.id == Showtime.theatre_id)
            .where(Showtime.id == showtime_id)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Showtime not found")
    showtime, movie, theatre = row

    seats = (
        await db.scalars(
            select(Seat)
            .where(Seat.theatre_id == showtime.theatre_id)
            .order_by(Seat.row_label, Seat.seat_number)
        )
    ).all()
    booked_seat_ids = set(
        (
            await db.scalars(
                select(Booking.seat_id).where(
                    Booking.showtime_id == showtime_id,
                    Booking.status == BookingStatus.CONFIRMED,
                )
            )
        ).all()
    )
    keys = [hold_key(showtime_id, seat.id) for seat in seats]
    held_values = await redis.mget(keys) if keys else []

    seat_items = []
    for seat, held_by in zip(seats, held_values, strict=True):
        seat_status = "BOOKED" if seat.id in booked_seat_ids else "HELD" if held_by else "AVAILABLE"
        seat_items.append(
            SeatMapItem(
                id=seat.id,
                row_label=seat.row_label,
                seat_number=seat.seat_number,
                seat_type=seat.seat_type,
                status=seat_status,
            )
        )

    return SeatMapResponse(
        showtime_id=showtime.id,
        movie_title=movie.title,
        theatre_name=theatre.name,
        starts_at=showtime.starts_at,
        price=showtime.price,
        seats=seat_items,
    )

