from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

EventStatus = Literal["draft", "published", "live", "closed"]


class EventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=80)
    start_ts: AwareDatetime
    end_ts: AwareDatetime
    venue: str | None = Field(default=None, max_length=255)
    topic_tags: list[str] = Field(default_factory=list, max_length=50)
    cost: Decimal | None = Field(default=None, ge=0)
    budget_planned: Decimal | None = Field(default=None, ge=0)
    expected_size: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_event_window(self) -> "EventCreate":
        if self.start_ts.utcoffset() != timedelta(0) or self.end_ts.utcoffset() != timedelta(0):
            raise ValueError("Event timestamps must use UTC")
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be later than start_ts")
        return self


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: str = Field(validation_alias="event_type", serialization_alias="type")
    start_ts: datetime
    end_ts: datetime
    venue: str | None
    topic_tags: list[str]
    cost: Decimal | None
    budget_planned: Decimal | None
    budget_actual: Decimal | None
    expected_size: int | None
    status: EventStatus
