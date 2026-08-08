"""Add refunded payment lifecycle and confirmed-booking uniqueness.

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


PAYMENT_STATUSES = (
    "PENDING",
    "INITIATING",
    "SUCCEEDED",
    "FAILED",
    "INITIATION_FAILED",
    "SUCCEEDED_NO_HOLD",
    "CONFLICT_REFUND_REQUIRED",
    "REFUNDED",
)


def upgrade() -> None:
    op.create_check_constraint(
        "ck_payments_status",
        "payments",
        "status IN ({})".format(", ".join(f"'{status}'" for status in PAYMENT_STATUSES)),
    )
    op.drop_constraint("uq_booking_showtime_seat", "bookings", type_="unique")
    op.create_index(
        "uq_booking_showtime_seat",
        "bookings",
        ["showtime_id", "seat_id"],
        unique=True,
        postgresql_where=sa.text("status = 'CONFIRMED'"),
    )


def downgrade() -> None:
    op.drop_index("uq_booking_showtime_seat", table_name="bookings")
    op.create_unique_constraint("uq_booking_showtime_seat", "bookings", ["showtime_id", "seat_id"])
    op.drop_constraint("ck_payments_status", "payments", type_="check")
