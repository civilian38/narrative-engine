from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class TemplateCharacterBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    background_description: str
    initial_status: str


class TemplateCharacterCreate(TemplateCharacterBase):
    template_narrative_id: int


class TemplateCharacterUpdate(BaseModel):
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


class TemplateCharacterRetrieve(TemplateCharacterBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_narrative_id: int


class TemplateCharacterList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    background_description: str