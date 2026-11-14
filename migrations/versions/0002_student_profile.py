"""Create the student profile table.

Revision ID: 0002_student_profile
Revises: 0001_phase0
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0002_student_profile"
down_revision: str | None = "0001_phase0"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "student_profile",
        sa.Column("student_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "interests",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column(
            "availability",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("budget_pref", sa.Integer(), nullable=True),
        sa.Column("year_type", sa.String(length=50), nullable=True),
        sa.Column("interest_embedding", Vector(dim=1536), nullable=True),
        sa.Column(
            "learned_weights",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("student_hash"),
    )


def downgrade() -> None:
    op.drop_table("student_profile")
