import json
import asyncio
from dataclasses import dataclass
import logging
from llama_cpp import Llama
from typing import Any, Iterator
from pydantic import TypeAdapter, BaseModel, ValidationError

from narrative_engine.exceptions import (
    ExternalServiceError,
    InvalidModelResponseError,
    InvalidOperationError,
    NarrativeEngineError,
)
from narrative_engine.domain.schemas.llm_io import StoryContentItem, StoryCreationResponse, CharacterUpdateResponse
from narrative_engine.domain.database import Database
from narrative_engine.services.llm_service import LLMService


logger = logging.getLogger(__name__)


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
                    raise InvalidModelResponseError(
                        "Unexpected JSON closing delimiter."
                    )

                expected = "{" if c == "}" else "["

                if self.stack[-1][0] != expected:
                    raise InvalidModelResponseError(
                        "Mismatched JSON delimiters."
                    )

                self.stack[-1] += c
                popped = self.stack.pop()

                # Append the completed structure to its parent object or array.
                if self.stack:
                    self.stack[-1] += popped

                # Validate only nested objects, excluding the root object.
                if c == "}" and self.stack:
                    try:
                        data = json.loads(popped)
                    except json.JSONDecodeError as e:
                        raise InvalidModelResponseError(
                            f"The model returned malformed JSON: {e.msg} at character {e.pos}."
                        ) from e

                    if isinstance(data, dict):
                        kind = data.get("kind")

                        if kind in {"Narration", "Dialogue"}:
                            try:
                                yield self.content_adapter.validate_python(
                                    data,
                                    context=validation_context,
                                )
                            except ValidationError as e:
                                raise InvalidModelResponseError(
                                    f"The model returned invalid story content: {e}"
                                ) from e

                continue

            # Append ordinary characters to the current structure.
            if self.stack:
                self.stack[-1] += c

    def finish(self) -> None:
        if self.stack or self.in_string:
            raise InvalidModelResponseError(
                "The model response ended before the JSON document was complete."
            )

@dataclass
class LLMTask:
    user_input: str | None
    prompt: str
    response_model: type[BaseModel]
    error_history: str
    kwargs: dict[str, int]
    yield_response_type: list[type[BaseModel]] | None = None
    validation_context: Any | None = None
    retry_count: int = 0
    max_retries: int = 3


class LocalModelService:
    def __init__(
        self,
        database: Database,
        model_path: str,
        n_gpu_layers: int,
        n_ctx: int,
        verbose: bool,
        max_tokens: int = 128000,
        temperature: float = 0.8,
        repeat_penalty: float = 1.1,
    ):
        self.raw_response: list[str] = []
        self.database = database
        self.llm = Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            verbose=verbose,
        )
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.repeat_penalty = repeat_penalty
        self.llm_service = LLMService(database)
        self.queue: asyncio.Queue[LLMTask] = asyncio.Queue()

    async def schedule_story_creation(
        self,
        session_narrative_id: int,
        user_input: str,
    ):
        allowed_ids, prompt = await asyncio.to_thread(
            lambda: self.llm_service.create_story_prompt(
                session_narrative_id,
                user_input, return_allowed_ids=True
            )
        )
        await self.queue.put(
            LLMTask(
                user_input=user_input,
                prompt=prompt,
                response_model=StoryCreationResponse,
                error_history="",
                kwargs={
                    "session_narrative_id": session_narrative_id},
                yield_response_type=None,
                validation_context=LLMService.allowed_id_config_generator(allowed_ids)
            )
        )

    async def schedule_character_update(
        self,
        session_character_id: int,
        session_turn_id: int,
    ):
        allowed_ids, prompt = await asyncio.to_thread(
            lambda: self.llm_service.create_character_update_prompt(
                session_character_id,
                return_allowed_ids=True
            )
        )
        await self.queue.put(
            LLMTask(
                user_input=None,
                prompt=prompt,
                response_model=CharacterUpdateResponse,
                error_history="",
                kwargs={
                    "session_turn_id": session_turn_id,
                    "session_character_id": session_character_id,
                },
                yield_response_type=None,
                validation_context=LLMService.allowed_id_config_generator(allowed_ids)
            )
        )

    async def schedule_worker(self):
        while True:
            task = await self.queue.get()

            try:
                await self.process_task(task)

            except asyncio.CancelledError:
                raise

            except Exception as e:
                logger.exception(f"LLM task processing failed: {e}")

            finally:
                self.queue.task_done()

    async def process_task(self, task: LLMTask):
        response = await asyncio.to_thread(
            lambda: self.llm.create_chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": task.prompt + task.error_history,
                    }
                 ],
                response_format={
                    "type": "json_object",
                    "schema": task.response_model.model_json_schema(),
                 },
                max_tokens=self.max_tokens,
                 temperature=self.temperature,
                 repeat_penalty=self.repeat_penalty,
            )
        )
        response_text = response["choices"][0]["message"]["content"]

        if task.response_model == StoryCreationResponse:
            try:
                story_validated_data = StoryCreationResponse.model_validate_json(
                    response_text,
                    context=task.validation_context
                )

                if task.user_input is None:
                    raise InvalidOperationError(
                        "user input is None in story creation"
                    )
                if task.kwargs.get("session_narrative_id") is None:
                    raise InvalidOperationError(
                        "session narrative id is None in story creation"
                    )
                story_pushed_data = await asyncio.to_thread(
                    lambda: self.llm_service.push_story_creation_result(
                        task.kwargs["session_narrative_id"],
                        task.user_input,
                        story_validated_data
                    )
                )


                for character_id in story_validated_data.involved_character_ids:
                    await self.schedule_character_update(character_id, story_pushed_data.id)

            except ValidationError as e:
                error_summary = "; ".join(
                    f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}"
                    for err in e.errors()
                )
                feedback = (
                    "=====\n"
                    "The previous JSON response failed schema validation.\n"
                    f"Validation errors: {error_summary}\n"
                    "Correct the errors and regenerate the complete response.\n"
                    "Return a JSON object only."
                )
                if task.retry_count < task.max_retries:

                    await self.queue.put(
                        LLMTask(
                            user_input=task.user_input,
                            prompt=task.prompt,
                            response_model=task.response_model,
                            error_history=task.error_history + '\n' + feedback,
                            kwargs=task.kwargs,
                            yield_response_type=task.yield_response_type,
                            validation_context=task.validation_context,
                            retry_count=task.retry_count + 1,
                            max_retries=task.max_retries,
                        )
                    )

                else:
                    logger.error("LLM validation retry limit exceeded")

        elif task.response_model == CharacterUpdateResponse:
            try:
                character_validated_data = CharacterUpdateResponse.model_validate_json(
                    response_text,
                    context=task.validation_context
                )

                if task.kwargs.get("session_character_id") is None:
                    raise InvalidOperationError(
                        "session_character_id is None in story creation"
                    )
                if task.kwargs.get("session_turn_id") is None:
                    raise InvalidOperationError(
                        "session_turn_id is None in story creation"
                    )
                character_pushed_data = await asyncio.to_thread(
                    lambda: self.llm_service.push_character_update_result(
                        task.kwargs["session_character_id"],
                        task.kwargs["session_turn_id"],
                        character_validated_data
                    )
                )


            except ValidationError as e:
                error_summary = "; ".join(
                    f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}"
                    for err in e.errors()
                )
                feedback = (
                    "=====\n"
                    "The previous JSON response failed schema validation.\n"
                    f"Validation errors: {error_summary}\n"
                    "Correct the errors and regenerate the complete response.\n"
                    "Return a JSON object only."
                )
                if task.retry_count < task.max_retries:

                    await self.queue.put(
                        LLMTask(
                            user_input=task.user_input,
                            prompt=task.prompt,
                            response_model=task.response_model,
                            error_history=task.error_history + '\n' + feedback,
                            kwargs=task.kwargs,
                            yield_response_type=task.yield_response_type,
                            validation_context=task.validation_context,
                            retry_count=task.retry_count + 1,
                            max_retries=task.max_retries,
                        )
                    )

                else:
                    logger.error("LLM validation retry limit exceeded")

        else:
            raise InvalidOperationError(
                f"Invalid task added to asyncio queue: {str(task.response_model)}"
            )

    def get_chunk_response[T: BaseModel](
        self,
        user_input: str,
        response_model: type[T],
        validation_context: Any | None = None,
        max_tokens: int = 128000,
        temperature: float = 0.8,
        repeat_penalty: float = 1.1,
    ):
        try:
            response = self.llm.create_chat_completion(
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

        except NarrativeEngineError:
            raise
        except Exception as e:
            raise ExternalServiceError(
                f"The local model request failed: {e}"
            ) from e

    def get_validated_response[T: BaseModel](
        self,
        response_model: type[T],
        validation_context: Any | None = None,
    ) -> T:
        if not self.raw_response:
            raise InvalidOperationError(
                "No streamed model response is available. Call get_chunk_response() first."
            )

        try:
            return response_model.model_validate_json(
                "".join(self.raw_response),
                context=validation_context,
            )
        except ValidationError as e:
            raise InvalidModelResponseError(
                f"The streamed model response failed schema validation: {e}"
            ) from e


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
            "max_retries must be a non-negative integer."
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
            raise ExternalServiceError(
                f"The local model request failed: {e}"
            ) from e

        output = response["choices"][0]["message"]["content"]

        if not output:
            raise InvalidModelResponseError(
                "The local model returned an empty response."
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
                raise InvalidModelResponseError(
                    f"The local model returned invalid JSON after "
                    f"{max_retries + 1} attempts: {error_summary}"
                ) from e

            feedback = (
                "The previous JSON response failed schema validation.\n"
                f"Validation errors: {error_summary}\n"
                "Correct the errors and regenerate the complete response.\n"
                "Return a JSON object only."
            )

            messages.append(
                {
                    "role": "user",
                    "content": feedback,
                }
            )

    raise InvalidModelResponseError(
        "The local model response retry loop ended without a valid response."
    )
