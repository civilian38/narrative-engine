import os
from dotenv import load_dotenv

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from narrative_engine.config import GEMINI_MODEL
from narrative_engine.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    InvalidModelResponseError,
    InvalidOperationError,
)


def _validate_allowed_ids(allowed_ids: list[int]) -> set[int]:
    if not allowed_ids:
        raise InvalidOperationError("At least one allowed character ID is required.")
    id_set = set(allowed_ids)
    if len(allowed_ids) != len(id_set):
        raise InvalidOperationError("allowed_ids must not contain duplicate IDs.")
    return id_set


def generate_structured_response[T: BaseModel](
    prompt: str,
    response_model: type[T],
    allowed_ids: list[int] | None = None,
    max_retries: int = 2,
) -> T:
    load_dotenv()

    if max_retries < 0:
        raise InvalidOperationError("max_retries must be a non-negative integer.")

    valid_id_set = (
        _validate_allowed_ids(allowed_ids) if allowed_ids is not None else None
    )
    validation_context = (
        {"allowed_ids": valid_id_set} if valid_id_set is not None else None
    )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ConfigurationError(
            "GEMINI_API_KEY is not set. Configure it before requesting Gemini responses."
        )

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        raise ExternalServiceError(f"Could not initialize the Gemini client: {e}") from e
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=response_model.model_json_schema(),
    )

    # Keep a content list for Gemini's multi-turn correction requests.
    contents: list[types.Content] = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        )
    ]

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )
        except Exception as e:
            raise ExternalServiceError(f"The Gemini request failed: {e}") from e

        if not response.text:
            raise InvalidModelResponseError("Gemini returned an empty response.")

        try:
            return response_model.model_validate_json(
                response.text,
                context=validation_context,
            )
        except ValidationError as e:
            error_summary = "; ".join(err["msg"] for err in e.errors())

            if attempt == max_retries:
                raise InvalidModelResponseError(
                    f"Gemini returned an invalid response after {max_retries + 1} "
                    f"attempts: {error_summary}"
                ) from e

            # Add the invalid response as a model turn.
            contents.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=response.text)],
                )
            )

            # Ask the model to correct the response and include allowed IDs.
            id_guide = (
                f"\nUse only IDs from this allowed list: {sorted(valid_id_set)}."
                if valid_id_set is not None
                else ""
            )
            feedback = (
                f"The previous JSON response failed schema validation.\n"
                f"Validation errors: {error_summary}{id_guide}\n"
                f"Correct the errors and regenerate the complete JSON response."
            )
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=feedback)],
                )
            )

    raise InvalidModelResponseError(
        "The Gemini response retry loop ended without a valid response."
    )
