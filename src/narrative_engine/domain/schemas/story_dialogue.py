from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from narrative_engine.domain.models import DialogueType
from narrative_engine.exceptions import InvalidOperationError


class StoryDialogueBase(BaseModel):
    content: str
    position: int = Field(ge=0)
    kind: DialogueType


class StoryDialogueCreate(StoryDialogueBase):
    story_turn_id: int
    speaker_id: int | None = None

    @model_validator(mode="after")
    def validate_speaker(self):
        if self.kind == DialogueType.Dialogue:
            if self.speaker_id is None:
                raise InvalidOperationError(
                    "Dialogue must have a speaker"
                )

        elif self.kind == DialogueType.Narration:
            if self.speaker_id is not None:
                raise InvalidOperationError(
                    "Narration cannot have a speaker"
                )

        return self


class StoryDialogueUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str | None = None
    position: int | None = Field(
        default=None,
        ge=0,
    )
    kind: DialogueType | None = None
    speaker_id: int | None = None

    @field_validator(
        "content",
        "position",
        "kind",
    )
    @classmethod
    def reject_none(cls, value):
        if value is None:
            raise InvalidOperationError(
                "Field cannot be null"
            )
        return value

    @model_validator(mode="after")
    def validate_speaker(self):
        if not {
            "kind",
            "speaker_id",
        }.issubset(self.model_fields_set):
            return self

        if self.kind == DialogueType.Dialogue:
            if self.speaker_id is None:
                raise InvalidOperationError(
                    "Dialogue must have a speaker"
                )

        elif self.kind == DialogueType.Narration:
            if self.speaker_id is not None:
                raise InvalidOperationError(
                    "Narration cannot have a speaker"
                )

        return self


class StoryDialogueRetrieve(StoryDialogueBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    story_turn_id: int
    speaker_id: int | None


class StoryDialogueList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    story_turn_id: int
    content: str
    position: int
    kind: DialogueType
    speaker_id: int | None
