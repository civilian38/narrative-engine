from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from narrative_engine.exceptions import InvalidOperationError


class SessionCharacterOpinionBase(BaseModel):
    opinion: str = Field(min_length=1, max_length=150)


class SessionCharacterOpinionCreate(SessionCharacterOpinionBase):
    session_narrative_id: int
    from_character_id: int
    to_character_id: int

    @field_validator("from_character_id", "to_character_id")
    @classmethod
    def validate_character_id(cls, value):
        if value <= 0:
            raise InvalidOperationError(
                "Character ID must be positive"
            )
        return value


class SessionCharacterOpinionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opinion: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )

    @field_validator("opinion")
    @classmethod
    def reject_none(cls, value):
        if value is None:
            raise InvalidOperationError(
                "Field cannot be null"
            )
        return value


class SessionCharacterOpinionRetrieve(SessionCharacterOpinionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_narrative_id: int
    from_character_id: int
    to_character_id: int


class SessionCharacterOpinionList(SessionCharacterOpinionRetrieve):
    pass


class SessionCharacterOpinionToOthers(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    to_character_id: int
    opinion: str


class SessionCharacterOpinionFromOthers(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_character_id: int
    opinion: str