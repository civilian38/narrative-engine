from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

class SessionCharacterMemoryBase(BaseModel):
    memory: str = Field(min_length=1)


class SessionCharacterMemoryCreate(SessionCharacterMemoryBase):
    session_character_id: int
    session_turn_id: int

    @field_validator("session_character_id", "session_turn_id")
    @classmethod
    def validate_resource_id(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Resource IDs must be positive integers.")
        return value


class SessionCharacterMemoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory: str | None = Field(default=None, min_length=1)

    @field_validator("memory")
    @classmethod
    def reject_none(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("memory cannot be null.")
        return value


class SessionCharacterMemoryRetrieve(SessionCharacterMemoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_character_id: int
    session_turn_id: int


class SessionCharacterMemoryList(SessionCharacterMemoryRetrieve):
    pass


class SessionCharacterMemoryCharacterList(SessionCharacterMemoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_turn_id: int
