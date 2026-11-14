"""Initialize the Phase 0 migration chain.

Revision ID: 0001_phase0
Revises:
Create Date: 2026-11-14
"""

from collections.abc import Sequence

revision: str = "0001_phase0"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
