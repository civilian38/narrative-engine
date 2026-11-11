from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class CharacterTemplateBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    background_description: str
    initial_status: str


class CharacterTemplateCreate(CharacterTemplateBase):
    narrative_template_id: int


class CharacterTemplateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    background_description: str | None = None
    initial_status: str | None = None

    @field_validator(
        "name",
        "background_description",
        "initial_status",
    )
    @classmethod
    def reject_none(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class CharacterTemplateRetrieve(CharacterTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    narrative_template_id: int


class CharacterTemplateList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    background_description: str