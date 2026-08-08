from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class HoldStatus(str, enum.Enum):
    HELD = "HELD"
    CONSUMED = "CONSUMED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    INITIATING = "INITIATING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    INITIATION_FAILED = "INITIATION_FAILED"
    SUCCEEDED_NO_HOLD = "SUCCEEDED_NO_HOLD"
    CONFLICT_REFUND_REQUIRED = "CONFLICT_REFUND_REQUIRED"
    REFUNDED = "REFUNDED"


class BookingStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


def enum_column(enum_type: type[enum.Enum], name: str) -> SqlEnum:
    return SqlEnum(enum_type, name=name, native_enum=False, length=40)


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    poster_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    showtimes: Mapped[list[Showtime]] = relationship(back_populates="movie")


class Theatre(Base):
    __tablename__ = "theatres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    seats: Mapped[list[Seat]] = relationship(back_populates="theatre")
    showtimes: Mapped[list[Showtime]] = relationship(back_populates="theatre")


class Showtime(Base):
    __tablename__ = "showtimes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    theatre_id: Mapped[int] = mapped_column(ForeignKey("theatres.id", ondelete="CASCADE"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    movie: Mapped[Movie] = relationship(back_populates="showtimes")
    theatre: Mapped[Theatre] = relationship(back_populates="showtimes")


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("theatre_id", "row_label", "seat_number", name="uq_seat_position"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    theatre_id: Mapped[int] = mapped_column(ForeignKey("theatres.id", ondelete="CASCADE"), nullable=False)
    row_label: Mapped[str] = mapped_column(String(4), nullable=False)
    seat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_type: Mapped[str] = mapped_column(String(30), nullable=False, default="STANDARD")

    theatre: Mapped[Theatre] = relationship(back_populates="seats")


class Hold(Base):
    __tablename__ = "holds"
    __table_args__ = (
        Index("ix_holds_showtime_seat", "showtime_id", "seat_id"),
        CheckConstraint("expires_at > created_at", name="ck_hold_expiry_after_creation"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    showtime_id: Mapped[int] = mapped_column(ForeignKey("showtimes.id", ondelete="CASCADE"), nullable=False)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id", ondelete="CASCADE"), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    status: Mapped[HoldStatus] = mapped_column(
        enum_column(HoldStatus, "hold_status"), nullable=False, default=HoldStatus.HELD
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        Index(
            "uq_booking_showtime_seat",
            "showtime_id",
            "seat_id",
            unique=True,
            postgresql_where=text("status = 'CONFIRMED'"),
            sqlite_where=text("status = 'CONFIRMED'"),
        ),
        UniqueConstraint("hold_id", name="uq_booking_hold"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    hold_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("holds.id", ondelete="RESTRICT"), nullable=False)
    showtime_id: Mapped[int] = mapped_column(ForeignKey("showtimes.id", ondelete="RESTRICT"), nullable=False)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id", ondelete="RESTRICT"), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        enum_column(BookingStatus, "booking_status"), nullable=False, default=BookingStatus.CONFIRMED
    )
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'INITIATING', 'SUCCEEDED', 'FAILED', 'INITIATION_FAILED', "
            "'SUCCEEDED_NO_HOLD', 'CONFLICT_REFUND_REQUIRED', 'REFUNDED')",
            name="ck_payments_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hold_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("holds.id", ondelete="RESTRICT"), nullable=False, unique=True)
    booking_ref: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    gateway_payment_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BDT")
    status: Mapped[PaymentStatus] = mapped_column(
        enum_column(PaymentStatus, "payment_status"), nullable=False, default=PaymentStatus.PENDING
    )
    initiation_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(1000))
    revenue_counted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    succeeded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list[PaymentEvent]] = relationship(back_populates="payment")


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    event_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)
    gateway_payment_id: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    payment: Mapped[Payment] = relationship(back_populates="events")
