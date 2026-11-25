from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from .template_character import TemplateCharacterList
from .session_narrative import SessionNarrativeListBase


class TemplateNarrativeBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    template_description: str | None = None
    world_description: str
    initial_situation: str


class TemplateNarrativeCreate(TemplateNarrativeBase):
    pass


class TemplateNarrativeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    world_description: str | None = None
    initial_situation: str | None = None
    template_description: str | None = None

    @field_validator(
        "name",
        "world_description",
        "initial_situation",
    )
    @classmethod
    def reject_none(cls, value):
        if value is None:
            raise ValueError("Fields in a template narrative update cannot be null.")
        return value


class TemplateNarrativeRetrieve(TemplateNarrativeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int

    template_characters: list[TemplateCharacterList] = Field(
        default_factory=list
    )

    session_narratives: list[SessionNarrativeListBase] = Field(
        default_factory=list
    )


class TemplateNarrativeList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    template_description: str | None = None
