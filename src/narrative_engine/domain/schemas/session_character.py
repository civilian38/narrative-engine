
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)
from .session_character_opinion import (
    SessionCharacterOpinionToOthers,
    SessionCharacterOpinionFromOthers,
)


class SessionCharacterBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    background_description: str
    status: str


class SessionCharacterCreate(SessionCharacterBase):
    session_narrative_id: int


class SessionCharacterUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    background_description: str | None = None
    status: str | None = None

    @field_validator(
        "name",
        "background_description",
        "status",
    )
    @classmethod
    def reject_none(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class SessionCharacterRetrieve(SessionCharacterBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_narrative_id: int

    opinions_to_others: list[SessionCharacterOpinionToOthers] = Field(
        default_factory=list
    )

    opinions_from_others: list[SessionCharacterOpinionFromOthers] = Field(
        default_factory=list
    )


class SessionCharacterList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    background_description: str
    status: str
