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
    pass


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

    session_characters: list[SessionCharacterList] = Field(
        default_factory=list
    )


class SessionNarrativeList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
