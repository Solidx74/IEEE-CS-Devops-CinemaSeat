import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Movie, Seat, Showtime, Theatre


async def seed() -> None:
    async with SessionLocal() as session:
        if await session.scalar(select(Movie.id).limit(1)) is not None:
            return

        movies = [
            Movie(id=1, title="The Last Orbit", description="A stranded crew races a dying star.", duration_minutes=128),
            Movie(id=2, title="Dhaka After Rain", description="Two strangers cross paths through one monsoon night.", duration_minutes=112),
            Movie(id=3, title="Semaphore", description="A codebreaker discovers a message meant for tomorrow.", duration_minutes=104),
        ]
        theatres = [
            Theatre(id=1, name="CinemaSeat Bashundhara", city="Dhaka"),
            Theatre(id=2, name="CinemaSeat Jamuna", city="Dhaka"),
        ]
        seats: list[Seat] = []
        seat_id = 1
        for theatre_id in (1, 2):
            for row in "ABCD":
                for number in range(1, 11):
                    seats.append(
                        Seat(
                            id=seat_id,
                            theatre_id=theatre_id,
                            row_label=row,
                            seat_number=number,
                            seat_type="PREMIUM" if row == "D" else "STANDARD",
                        )
                    )
                    seat_id += 1

        base = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
        showtimes = [
            Showtime(id=1, movie_id=1, theatre_id=1, starts_at=base + timedelta(hours=12), price=Decimal("450.00")),
            Showtime(id=2, movie_id=1, theatre_id=2, starts_at=base + timedelta(hours=15), price=Decimal("500.00")),
            Showtime(id=3, movie_id=2, theatre_id=1, starts_at=base + timedelta(hours=18), price=Decimal("400.00")),
            Showtime(id=4, movie_id=3, theatre_id=2, starts_at=base + timedelta(days=1, hours=12), price=Decimal("550.00")),
        ]

        session.add_all([*movies, *theatres, *seats, *showtimes])
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
