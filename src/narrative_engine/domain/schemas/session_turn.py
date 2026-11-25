from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from .session_dialogue import SessionDialogueList


class SessionTurnBase(BaseModel):
    turn_index: int = Field(ge=0)
    user_input: str


class SessionTurnCreate(SessionTurnBase):
    session_narrative_id: int


class SessionTurnUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_input: str | None = None

    @field_validator("user_input")
    @classmethod
    def reject_none(cls, value):
        if value is None:
            raise ValueError("user_input cannot be null.")
        return value


class SessionTurnRetrieve(SessionTurnBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_narrative_id: int

    session_dialogues: list[SessionDialogueList] = Field(
        default_factory=list
    )


class SessionTurnList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    turn_index: int
    user_input: str
