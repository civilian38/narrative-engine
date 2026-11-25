
import json
from llama_cpp import Llama
from typing import Any, Iterator
from pydantic import TypeAdapter, BaseModel, ValidationError

from narrative_engine.exceptions import InvalidOperationError, OuterAPIError
from narrative_engine.domain.schemas.llm_io import StoryContentItem


class StreamJsonParser:
    def __init__(self):
        self.stack: list[str] = []
        self.in_string = False
        self.escaped = False

        self.content_adapter = TypeAdapter(StoryContentItem)

    def stream_in(
        self,
        chunk: str,
        validation_context: Any | None = None,
    ) -> Iterator[StoryContentItem]:

        for c in chunk:

            # Ignore JSON structural characters inside strings.
            if self.in_string:
                self.stack[-1] += c

                if self.escaped:
                    self.escaped = False
                elif c == "\\":
                    self.escaped = True
                elif c == '"':
                    self.in_string = False

                continue

            # Handle the beginning of a string.
            if c == '"':
                if self.stack:
                    self.stack[-1] += c
                    self.in_string = True
                continue

            # Handle the beginning of an object or array.
            if c in {"{", "["}:
                if self.stack:
                    self.stack[-1] += c

                self.stack.append(c)
                continue

            # Handle the end of an object or array.
            if c in {"}", "]"}:
                if not self.stack:
                    raise OuterAPIError(
                        "Unexpected JSON closing delimiter."
                    )

                expected = "{" if c == "}" else "["

                if self.stack[-1][0] != expected:
                    raise OuterAPIError(
                        "Mismatched JSON delimiters."
                    )

                self.stack[-1] += c
                popped = self.stack.pop()

                # Append the completed structure to its parent object or array.
                if self.stack:
                    self.stack[-1] += popped

                # Validate only nested objects, excluding the root object.
                if c == "}" and self.stack:
                    data = json.loads(popped)

                    if isinstance(data, dict):
                        kind = data.get("kind")

                        if kind in {"Narration", "Dialogue"}:
                            try:
                                yield self.content_adapter.validate_python(
                                    data,
                                    context=validation_context,
                                )
                            except ValidationError as e:
                                raise OuterAPIError(
                                    f"Invalid story content: {e}"
                                ) from e

                continue

            # Append ordinary characters to the current structure.
            if self.stack:
                self.stack[-1] += c

    def finish(self) -> None:
        if self.stack or self.in_string:
            raise OuterAPIError(
                "LLM JSON stream ended unexpectedly."
            )


class LocalModelService:
    def __init__(self):
        self.raw_response: list[str] = []

    def get_chunk_response[T: BaseModel](
        self,
        llm: Llama,
        user_input: str,
        response_model: type[T],
        validation_context: Any | None = None,
        max_tokens: int = 128000,
        temperature: float = 0.8,
        repeat_penalty: float = 1.1,
    ):
        try:
            response = llm.create_chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": user_input
                    }
                ],
                response_format={
                    "type": "json_object",
                    "schema": response_model.model_json_schema(),
                },
                max_tokens=max_tokens,
                temperature=temperature,
                repeat_penalty=repeat_penalty,
                stream=True,
            )

            parser = StreamJsonParser()
            self.raw_response = list()

            for chunk in response:
                content = chunk["choices"][0]["delta"].get("content")

                if content is None:
                    continue

                self.raw_response.append(content)
                yield from parser.stream_in(
                    content,
                    validation_context,
                )

            parser.finish()

        except Exception as e:
            raise OuterAPIError(
                f"llama.cpp API Error: {e}"
            ) from e

    def get_validated_response[T: BaseModel](
        self,
        response_model: type[T],
        validation_context: Any | None = None,
    ) -> T:
        if not self.raw_response:
            raise InvalidOperationError(
                "chunk response not executed"
            )

        return response_model.model_validate_json(
            "".join(self.raw_response),
            context=validation_context
        )


def generate_structured_response[T: BaseModel](
    llm: Llama,
    user_input: str,
    response_model: type[T],
    validation_context: Any | None = None,
    max_retries: int = 3,
    max_tokens: int = 128000,
    temperature: float = 0.8,
    repeat_penalty: float = 1.1,
) -> T:
    if max_retries < 0:
        raise InvalidOperationError(
            "max_retries should be non-negative integer"
        )

    messages = [
        {
            "role": "user",
            "content": user_input
        }
    ]

    for attempt in range(1 + max_retries):
        try:
            response = llm.create_chat_completion(
                messages=messages,
                response_format={
                    "type": "json_object",
                    "schema": response_model.model_json_schema(),
                },
                max_tokens=max_tokens,
                temperature=temperature,
                repeat_penalty=repeat_penalty,
            )
        except Exception as e:
            raise OuterAPIError(
                f"llama.cpp API Error: {e}"
            ) from e

        output = response["choices"][0]["message"]["content"]

        if not output:
            raise OuterAPIError(
                "llama.cpp Response is Empty"
            )

        try:
            return response_model.model_validate_json(
                output,
                context=validation_context
            )

        except ValidationError as e:
            error_summary = "; ".join(
                f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}"
                for err in e.errors()
            )

            if attempt == max_retries:
                raise OuterAPIError(
                    f"LLM 응답 검증에 최종 실패했습니다 "
                    f"({max_retries + 1}회 시도): {error_summary}"
                ) from e

            feedback = (
                "직전 JSON 응답이 Pydantic 검증에 실패했습니다.\n"
                f"검증 오류: {error_summary}\n"
                "검증 오류를 수정하여 전체 JSON을 다시 생성하세요.\n"
                "반드시 JSON 객체만 출력하세요."
            )

            messages.append(
                {
                    "role": "user",
                    "content": feedback,
                }
            )

    raise OuterAPIError(
        "Unexpected retry loop termination"
    )
