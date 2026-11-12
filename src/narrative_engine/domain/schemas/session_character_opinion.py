
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class SessionCharacterOpinionBase(BaseModel):
    opinion: str = Field(min_length=1, max_length=150)


class SessionCharacterOpinionCreate(SessionCharacterOpinionBase):
    from_character_id: int
    to_character_id: int

    @model_validator(mode="after")
    def reject_self_opinion(self):
        if self.from_character_id == self.to_character_id:
            raise ValueError(
                "A character cannot have an opinion about itself"
            )
        return self


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
            raise ValueError("Field cannot be null")
        return value


class SessionCharacterOpinionRetrieve(SessionCharacterOpinionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_character_id: int
    to_character_id: int


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