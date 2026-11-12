from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from .session_character import SessionCharacterList


class SessionNarrativeBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    world_description: str
    situation: str


class SessionNarrativeCreate(SessionNarrativeBase):
    narrative_template_id: int | None


class SessionNarrativeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    world_description: str | None = None
    situation: str | None = None

    @field_validator(
        "title",
        "world_description",
        "situation",
    )
    @classmethod
    def reject_none(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class SessionNarrativeRetrieve(SessionNarrativeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    narrative_template_id: int | None

    session_characters: list[SessionCharacterList] = Field(
        default_factory=list
    )


class SessionNarrativeListBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str


class SessionNarrativeList(SessionNarrativeListBase):
    narrative_template_id: int | None
