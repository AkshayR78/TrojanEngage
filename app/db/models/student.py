from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentProfile(Base):
    __tablename__ = "student_profile"

    student_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    interests: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    availability: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    budget_pref: Mapped[int | None] = mapped_column(Integer)
    year_type: Mapped[str | None] = mapped_column(String(50))
    interest_embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    learned_weights: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
