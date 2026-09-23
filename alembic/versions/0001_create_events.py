"""create events table

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    status = sa.Enum(
        "queued",
        "processing",
        "retrying",
        "completed",
        "failed",
        name="event_status",
    )
    status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_correlation_id", "events", ["correlation_id"])


def downgrade() -> None:
    op.drop_index("ix_events_correlation_id", table_name="events")
    op.drop_table("events")
    sa.Enum(name="event_status").drop(op.get_bind(), checkfirst=True)
