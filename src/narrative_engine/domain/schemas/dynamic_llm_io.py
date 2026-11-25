from enum import IntEnum
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    create_model,
)

from narrative_engine.exceptions import InvalidOperationError


class NarrationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["Narration"]
    content: str = Field(description="서술 내용")


def get_dialogue_output_model(
    allowed_ids: list[int],
) -> type[BaseModel]:
    if not allowed_ids:
        raise InvalidOperationError(
            "At least one allowed speaker ID is required to build the dialogue response model."
        )

    allowed_id_set = set(allowed_ids)
    if len(allowed_ids) != len(allowed_id_set):
        raise InvalidOperationError(
            "allowed_ids must not contain duplicate IDs."
        )

    speaker_id_enum = IntEnum(
        "SpeakerIDEnum",
        {f"ID_{item}": item for item in allowed_ids},
    )

    SpeakerID = Annotated[
        speaker_id_enum,
        AfterValidator(lambda x: x.value),
        PlainSerializer(int, return_type=int, when_used="json"),
    ]

    return create_model(
        "DialogueOutput",
        __config__=ConfigDict(extra="forbid"),
        kind=(Literal["Dialogue"], ...),
        speaker_name=(str, Field(description="발화한 인물의 이름")),
        speaker_id=(
            SpeakerID,
            Field(description=f"발화한 인물의 ID. 허용 값: {sorted(allowed_id_set)}"),
        ),
        content=(str, Field(description="대사 내용")),
    )


def get_dialogue_output_item(allowed_ids: list[int]):
    dialogue_output = get_dialogue_output_model(allowed_ids)
    return NarrationOutput | dialogue_output


def get_story_creation_response_model(
    allowed_ids: list[int],
) -> type[BaseModel]:
    dialogue_output_item = get_dialogue_output_item(allowed_ids)

    return create_model(
        "DialogueList",
        __config__=ConfigDict(extra="forbid"),
        contents=(
            list[dialogue_output_item],
            Field(description="순서대로 배열된 서술과 대사. 주의: 허용된 ID값을 가진 인물 외의 대사는 서술(Narration)으로 처리할것"),
        ),
        new_world_situation=(
            str,
            Field(description="이번 사건 이후 세계관의 상황")
        )
    )


def get_opinion_alter_model(
    allowed_ids: list[int],
) -> type[BaseModel]:
    if not allowed_ids:
        raise InvalidOperationError(
            "At least one allowed target character ID is required to build the opinion response model."
        )

    if len(allowed_ids) != len(set(allowed_ids)):
        raise InvalidOperationError(
            "The allowed target character ID list must not contain duplicate IDs."
        )

    allowed_id_set = set(allowed_ids)
    target_id_enum = IntEnum(
        "TargetIDEnum",
        {f"ID_{item}": item for item in allowed_ids},
    )

    TargetID = Annotated[
        target_id_enum,
        AfterValidator(lambda x: x.value),
        PlainSerializer(int, return_type=int, when_used="json"),
    ]

    return create_model(
        "OpinionAlter",
        __config__=ConfigDict(extra="forbid"),
        target_character_name=(
            str,
            Field(description="변경 대상 인물의 이름."),
        ),
        target_character_id=(
            TargetID,
            Field(description=f"변경 대상 인물 ID. 허용 값: {sorted(allowed_id_set)}"),
        ),
        new_opinion=(
            str,
            Field(
                max_length=150,
                description="대상 인물에 대해 새로 형성된 의견 (공백 포함 150자 이내)",
            ),
        ),
    )


def get_opinion_alter_list_model(
    allowed_ids: list[int],
) -> type[BaseModel]:
    opinion_alter_item = get_opinion_alter_model(allowed_ids)

    return create_model(
        "OpinionAlterList",
        __config__=ConfigDict(extra="forbid"),
        alter_data=(
            list[opinion_alter_item],
            Field(description="변경할 인물 의견 목록"),
        ),
    )


def get_character_change_response_model(
    session_character_ids: list[int],
) -> type[BaseModel]:
    opinion_alter_list = get_opinion_alter_list_model(
        session_character_ids
    )

    return create_model(
        "CharacterChange",
        __config__=ConfigDict(extra="forbid"),
        new_status=(
            str,
            Field(description="인물의 새 상태"),
        ),
        opinion_alter=(
            opinion_alter_list,
            Field(description="다른 인물들에 대한 의견 변경 목록. 의견을 변경할 필요가 있는 인물들에 대해서만 목록을 작성하라."),
        ),
    )
