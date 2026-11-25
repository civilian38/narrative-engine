from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from narrative_engine.domain.models import DialogueType
class SessionDialogueBase(BaseModel):
    content: str
    position: int = Field(ge=0)
    kind: DialogueType


class SessionDialogueCreate(SessionDialogueBase):
    session_turn_id: int
    speaker_id: int | None = None

    @model_validator(mode="after")
    def validate_speaker(self):
        if self.kind == DialogueType.Dialogue:
            if self.speaker_id is None:
                raise ValueError("A dialogue must have a speaker.")

        elif self.kind == DialogueType.Narration:
            if self.speaker_id is not None:
                raise ValueError("Narration cannot have a speaker.")

        return self


class SessionDialogueUpdate(BaseModel):
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
            raise ValueError("This field cannot be null.")
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
                raise ValueError("A dialogue must have a speaker.")

        elif self.kind == DialogueType.Narration:
            if self.speaker_id is not None:
                raise ValueError("Narration cannot have a speaker.")

        return self


class SessionDialogueRetrieve(SessionDialogueBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_turn_id: int
    speaker_id: int | None


class SessionDialogueList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_turn_id: int
    content: str
    position: int
    kind: DialogueType
    speaker_id: int | None
