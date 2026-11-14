from pydantic import BaseModel, ConfigDict, Field


class StudentProfileInput(BaseModel):
    interests: list[str] = Field(default_factory=list, max_length=50)
    goal: str = Field(min_length=1, max_length=500)
    availability: list[str] = Field(default_factory=list, max_length=50)
    budget_pref: int | None = Field(default=None, ge=0)
    year_type: str | None = Field(default=None, max_length=50)


class StudentProfileResponse(StudentProfileInput):
    model_config = ConfigDict(from_attributes=True)
