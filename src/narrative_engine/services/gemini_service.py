import os
from dotenv import load_dotenv

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from narrative_engine.config import GEMINI_MODEL
from narrative_engine.exceptions import InvalidOperationError, OuterAPIError


def _validate_allowed_ids(allowed_ids: list[int]) -> set[int]:
    if not allowed_ids:
        raise InvalidOperationError("허용된 인물 ID가 하나 이상 필요합니다.")
    id_set = set(allowed_ids)
    if len(allowed_ids) != len(id_set):
        raise InvalidOperationError("allowed_ids에 중복된 ID가 있습니다.")
    return id_set


def generate_structured_response[T: BaseModel](
    prompt: str,
    response_model: type[T],
    allowed_ids: list[int] | None = None,
    max_retries: int = 2,
) -> T:
    load_dotenv()

    valid_id_set = (
        _validate_allowed_ids(allowed_ids) if allowed_ids is not None else None
    )
    validation_context = (
        {"allowed_ids": valid_id_set} if valid_id_set is not None else None
    )

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=response_model.model_json_schema(),
    )

    # Gemini 멀티턴 대화를 위해 Content 리스트로 관리
    contents: list[types.Content] = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        )
    ]

    for attempt in range(max_retries + 1):
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=config,
        )

        if not response.text:
            raise OuterAPIError("Gemini Response is empty")

        try:
            return response_model.model_validate_json(
                response.text,
                context=validation_context,
            )
        except ValidationError as e:
            error_summary = "; ".join(err["msg"] for err in e.errors())

            if attempt == max_retries:
                raise OuterAPIError(
                    f"Gemini 응답 검증에 최종 실패했습니다 ({max_retries + 1}회 시도): {error_summary}"
                ) from e

            # 1. 잘못된 직전 응답을 'model' 턴으로 기록
            contents.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=response.text)],
                )
            )

            # 2. 검증 실패 사유와 허용 ID 안내를 'user' 턴으로 추가해 재요청
            id_guide = (
                f"\n반드시 허용된 ID 목록({sorted(valid_id_set)}) 내의 값만 사용하세요."
                if valid_id_set is not None
                else ""
            )
            feedback = (
                f"직전 JSON 출력이 스키마 규칙 검증에 실패했습니다.\n"
                f"오류 사유: {error_summary}{id_guide}\n"
                f"규칙을 준수하여 전체 JSON을 다시 생성하세요."
            )
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=feedback)],
                )
            )

    raise OuterAPIError("Unexpected retry loop termination")