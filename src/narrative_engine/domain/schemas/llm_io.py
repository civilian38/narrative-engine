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
            "Dialogue를 생성하려면 허용된 speaker ID가 하나 이상 필요합니다."
        )

    allowed_id_set = set(allowed_ids)
    if len(allowed_ids) != len(allowed_id_set):
        raise InvalidOperationError(
            "allowed_ids에 중복된 ID가 있습니다."
        )

    speaker_id_enum = IntEnum(
        "SpeakerIDEnum",
        {f"ID_{item}": item for item in allowed_ids},
    )

    def validate_speaker_id(value: IntEnum) -> int:
        speaker_id = int(value)
        if speaker_id not in allowed_ids:
            raise InvalidOperationError(
                f"허용되지 않은 speaker_id입니다: {speaker_id}"
            )
        return speaker_id

    SpeakerID = Annotated[
        speaker_id_enum,
        AfterValidator(validate_speaker_id),
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

    return Annotated[
        NarrationOutput | dialogue_output,
        Field(discriminator="kind"),
    ]


def get_dialogue_list_model(
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
    )


def get_opinion_alter_model(
    allowed_ids: list[int],
) -> type[BaseModel]:
    if not allowed_ids:
        raise InvalidOperationError(
            "OpinionAlter를 생성하려면 허용된 대상 인물 ID가 하나 이상 필요합니다."
        )

    if len(allowed_ids) != len(set(allowed_ids)):
        raise InvalidOperationError(
            "허용된 대상 인물 ID 목록에 중복된 ID가 있습니다."
        )

    allowed_id_set = set(allowed_ids)
    target_id_enum = IntEnum(
        "TargetIDEnum",
        {f"ID_{item}": item for item in allowed_ids},
    )

    def validate_target_id(value: IntEnum) -> int:
        target_id = int(value)
        if target_id not in allowed_id_set:
            raise InvalidOperationError(
                f"허용되지 않은 대상 인물 ID입니다: {target_id}"
            )
        return target_id

    TargetID = Annotated[
        target_id_enum,
        AfterValidator(validate_target_id),
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
                description="대상 인물에 대해 새로 형성된 의견"
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


def get_character_change_model(
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
            Field(description="다른 인물들에 대한 의견 변경"),
        ),
    )