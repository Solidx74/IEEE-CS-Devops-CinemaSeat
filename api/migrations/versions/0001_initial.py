"""Initial CinemaSeat schema.

Revision ID: 0001
Revises:
"""

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("poster_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "theatres",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "seats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("theatre_id", sa.Integer(), sa.ForeignKey("theatres.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_label", sa.String(4), nullable=False),
        sa.Column("seat_number", sa.Integer(), nullable=False),
        sa.Column("seat_type", sa.String(30), nullable=False),
        sa.UniqueConstraint("theatre_id", "row_label", "seat_number", name="uq_seat_position"),
    )
    op.create_table(
        "showtimes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("theatre_id", sa.Integer(), sa.ForeignKey("theatres.id", ondelete="CASCADE"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "holds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("showtime_id", sa.Integer(), sa.ForeignKey("showtimes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seat_id", sa.Integer(), sa.ForeignKey("seats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_email", sa.String(320), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("expires_at > created_at", name="ck_hold_expiry_after_creation"),
    )
    op.create_index("ix_holds_showtime_seat", "holds", ["showtime_id", "seat_id"])
    op.create_table(
        "bookings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reference", sa.String(40), nullable=False, unique=True),
        sa.Column("hold_id", sa.Uuid(), sa.ForeignKey("holds.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("showtime_id", sa.Integer(), sa.ForeignKey("showtimes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("seat_id", sa.Integer(), sa.ForeignKey("seats.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_email", sa.String(320), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("showtime_id", "seat_id", name="uq_booking_showtime_seat"),
        sa.UniqueConstraint("hold_id", name="uq_booking_hold"),
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("hold_id", sa.Uuid(), sa.ForeignKey("holds.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("booking_ref", sa.String(40), nullable=False, unique=True),
        sa.Column("gateway_payment_id", sa.String(80), unique=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("initiation_attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(1000)),
        sa.Column("revenue_counted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("succeeded_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "payment_events",
        sa.Column("event_id", sa.String(100), primary_key=True),
        sa.Column("payment_id", sa.Uuid(), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gateway_payment_id", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("payment_events")
    op.drop_table("payments")
    op.drop_table("bookings")
    op.drop_index("ix_holds_showtime_seat", table_name="holds")
    op.drop_table("holds")
    op.drop_table("showtimes")
    op.drop_table("seats")
    op.drop_table("theatres")
    op.drop_table("movies")

