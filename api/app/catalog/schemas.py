from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ShowtimeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    starts_at: datetime
    price: Decimal
    theatre_id: int
    theatre_name: str


class MovieSummary(BaseModel):
    id: int
    title: str
    description: str
    duration_minutes: int
    poster_url: str | None
    showtimes: list[ShowtimeSummary]


class SeatMapItem(BaseModel):
    id: int
    row_label: str
    seat_number: int
    seat_type: str
    status: str


class SeatMapResponse(BaseModel):
    showtime_id: int
    movie_title: str
    theatre_name: str
    starts_at: datetime
    price: Decimal
    seats: list[SeatMapItem]

