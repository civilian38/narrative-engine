from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from .character_template import CharacterTemplateList
from .session_narrative import SessionNarrativeListBase


class NarrativeTemplateBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    template_description: str | None = None
    world_description: str
    initial_situation: str


class NarrativeTemplateCreate(NarrativeTemplateBase):
    pass


class NarrativeTemplateUpdate(BaseModel):
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
            raise ValueError("Field cannot be null")
        return value


class NarrativeTemplateRetrieve(NarrativeTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int

    character_templates: list[CharacterTemplateList] = Field(
        default_factory=list
    )

    session_narratives: list[SessionNarrativeListBase] = Field(
        default_factory=list
    )


class NarrativeTemplateList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    template_description: str | None = None
