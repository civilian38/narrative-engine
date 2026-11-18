from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
)

from narrative_engine.exceptions import InvalidOperationError


def _extract_allowed_ids(info: ValidationInfo) -> set[int]:
    """검증 시 전달된 context에서 allowed_ids를 추출합니다."""
    if not info.context or "allowed_ids" not in info.context:
        raise InvalidOperationError("검증 컨텍스트에 'allowed_ids'가 필요합니다.")
    return set(info.context["allowed_ids"])


# ==========================================
# 1. Story Creation
# ==========================================

class NarrationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["Narration"]
    content: str = Field(description="서술 내용")


class DialogueOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["Dialogue"]
    speaker_name: str = Field(description="발화한 인물의 이름")
    speaker_id: int = Field(description="발화한 인물의 ID (프롬프트에 명시된 허용 ID만 사용)")
    content: str = Field(description="대사 내용")

    @field_validator("speaker_id")
    @classmethod
    def validate_speaker_id(cls, v: int, info: ValidationInfo) -> int:
        allowed_ids = _extract_allowed_ids(info)
        if v not in allowed_ids:
            raise ValueError(
                f"허용되지 않은 speaker_id({v})입니다. 허용된 ID: {sorted(allowed_ids)}"
            )
        return v


StoryContentItem = Annotated[
    NarrationOutput | DialogueOutput,
    Field(discriminator="kind"),
]


class StoryCreationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contents: list[StoryContentItem] = Field(
        description="순서대로 배열된 서술과 대사. 주의: 허용된 ID값을 가진 인물 외의 대사는 서술(Narration)로 처리할 것"
    )
    new_world_situation: str = Field(description="이번 사건 이후 세계관의 상황")


# ==========================================
# 2. Character Change
# ==========================================

class OpinionAlter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_character_name: str = Field(description="변경 대상 인물의 이름.")
    target_character_id: int = Field(description="변경 대상 인물 ID (프롬프트에 명시된 허용 ID만 사용)")
    new_opinion: str = Field(
        description="대상 인물에 대해 새로 형성된 의견 (공백 포함 150자 이내)"
    )

    @field_validator("target_character_id")
    @classmethod
    def validate_target_id(cls, v: int, info: ValidationInfo) -> int:
        allowed_ids = _extract_allowed_ids(info)
        if v not in allowed_ids:
            raise ValueError(
                f"허용되지 않은 target_character_id({v})입니다. 허용된 ID: {sorted(allowed_ids)}"
            )
        return v

    @field_validator("new_opinion")
    @classmethod
    def validate_opinion_length(cls, v: str) -> str:
        # API JSON Schema의 maxLength 지원 여부와 무관하게 애플리케이션 레벨에서 안전하게 검증
        if len(v) > 150:
            raise ValueError(f"new_opinion은 150자 이내여야 합니다. (현재 {len(v)}자)")
        return v


class OpinionAlterList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alter_data: list[OpinionAlter] = Field(description="변경할 인물 의견 목록")


class CharacterChangeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_status: str = Field(description="인물의 새 상태")
    opinion_alter: OpinionAlterList = Field(
        description="다른 인물들에 대한 의견 변경 목록. 의견을 변경할 필요가 있는 인물들에 대해서만 목록을 작성하라."
    )