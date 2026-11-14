from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, DateTime, ForeignKey, Integer, Numeric, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Event(Base):
    __tablename__ = "event"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("org.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column("type", String(80), nullable=False)
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    venue: Mapped[str | None] = mapped_column(String(255))
    topic_tags: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
        server_default=text("'{}'"),
    )
    cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    budget_planned: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    budget_actual: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    expected_size: Mapped[int | None] = mapped_column(Integer)
    headcount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="draft",
        server_default="draft",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )
