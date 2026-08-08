import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PayRequest(BaseModel):
    hold_id: uuid.UUID
    currency: str = Field(default="BDT", min_length=3, max_length=3)


class PayAcceptedResponse(BaseModel):
    payment_id: uuid.UUID
    booking_ref: str
    status: str
    poll_url: str


class PaymentStatusResponse(BaseModel):
    payment_id: uuid.UUID
    booking_ref: str
    gateway_payment_id: str | None
    status: str
    amount: Decimal
    currency: str
    booking_confirmed: bool
    created_at: datetime


class GatewayPaymentEvent(BaseModel):
    event_id: str
    payment_id: str
    booking_ref: str
    status: str
    amount: Decimal
    currency: str
    timestamp: datetime


class OtpSendRequest(BaseModel):
    phone: str = Field(min_length=5, max_length=30)


class OtpSendResponse(BaseModel):
    ref: str
    status: str


class OtpVerifyRequest(BaseModel):
    ref: str
    code: str = Field(min_length=4, max_length=10)


class OtpVerifyResponse(BaseModel):
    ref: str
    verified: bool
    error: str | None = None

