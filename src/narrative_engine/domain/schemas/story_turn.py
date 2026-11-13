from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from narrative_engine.exceptions import InvalidOperationError

from .story_dialogue import StoryDialogueList


class StoryTurnBase(BaseModel):
    turn_index: int = Field(ge=0)
    user_input: str


class StoryTurnCreate(StoryTurnBase):
    session_narrative_id: int


class StoryTurnUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_input: str | None = None

    @field_validator("user_input")
    @classmethod
    def reject_none(cls, value):
        if value is None:
            raise InvalidOperationError(
                "Field cannot be null"
            )
        return value


class StoryTurnRetrieve(StoryTurnBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_narrative_id: int

    story_dialogues: list[StoryDialogueList] = Field(
        default_factory=list
    )


class StoryTurnList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    turn_index: int
    user_input: str
