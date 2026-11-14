"""Create organization and event tables.

Revision ID: 0003_org_event
Revises: 0002_student_profile
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_org_event"
down_revision: str | None = "0002_student_profile"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "org",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column(
            "share_opt_in",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "anonymize",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("start_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("venue", sa.String(length=255), nullable=True),
        sa.Column(
            "topic_tags",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("cost", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("budget_planned", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("budget_actual", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("expected_size", sa.Integer(), nullable=True),
        sa.Column("headcount", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["org.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_org_id", "event", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_event_org_id", table_name="event")
    op.drop_table("event")
    op.drop_table("org")
