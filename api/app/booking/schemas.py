import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CreateHoldRequest(BaseModel):
    seat_id: int = Field(gt=0)
    customer_email: str = Field(min_length=3, max_length=320)


class HoldResponse(BaseModel):
    hold_id: uuid.UUID
    showtime_id: int
    seat_id: int
    status: str
    expires_at: datetime
    ttl_seconds: int


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reference: str
    showtime_id: int
    seat_id: int
    customer_email: str
    amount: Decimal
    status: str
    confirmed_at: datetime

