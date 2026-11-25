from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ValidationError

from narrative_engine.domain.models import DialogueType
from narrative_engine.domain.schemas.session_dialogue import SessionDialogueCreate
from narrative_engine.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    InvalidModelResponseError,
    OuterAPIError,
)
from narrative_engine.services import gemini_service, local_model_service


class ExampleResponse(BaseModel):
    value: int


def test_outer_api_error_remains_an_alias_for_external_service_error():
    assert OuterAPIError is ExternalServiceError


def test_invalid_dialogue_schema_raises_pydantic_validation_error():
    with pytest.raises(ValidationError, match="A dialogue must have a speaker"):
        SessionDialogueCreate(
            session_turn_id=1,
            kind=DialogueType.Dialogue,
            content="Hello",
            position=0,
        )


def test_gemini_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(gemini_service, "load_dotenv", lambda: None)

    with pytest.raises(ConfigurationError, match="GEMINI_API_KEY is not set"):
        gemini_service.generate_structured_response(
            prompt="Return a value.",
            response_model=ExampleResponse,
        )


def test_gemini_request_failure_is_reported_as_external_service_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class FakeModels:
        @staticmethod
        def generate_content(**kwargs):
            raise RuntimeError("connection refused")

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr(gemini_service.genai, "Client", FakeClient)

    with pytest.raises(ExternalServiceError, match="The Gemini request failed: connection refused"):
        gemini_service.generate_structured_response(
            prompt="Return a value.",
            response_model=ExampleResponse,
            max_retries=0,
        )


def test_gemini_invalid_model_response_has_its_own_error_type(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class FakeModels:
        @staticmethod
        def generate_content(**kwargs):
            return SimpleNamespace(text='{"value": "not-an-integer"}')

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr(gemini_service.genai, "Client", FakeClient)

    with pytest.raises(InvalidModelResponseError, match="invalid response after 1 attempts"):
        gemini_service.generate_structured_response(
            prompt="Return a value.",
            response_model=ExampleResponse,
            max_retries=0,
        )


def test_local_model_request_failure_is_reported_as_external_service_error():
    class FakeModel:
        @staticmethod
        def create_chat_completion(**kwargs):
            raise RuntimeError("server unavailable")

    with pytest.raises(ExternalServiceError, match="The local model request failed: server unavailable"):
        local_model_service.generate_structured_response(
            llm=FakeModel(),
            user_input="Return a value.",
            response_model=ExampleResponse,
            max_retries=0,
        )


def test_local_model_invalid_response_has_its_own_error_type():
    class FakeModel:
        @staticmethod
        def create_chat_completion(**kwargs):
            return {
                "choices": [
                    {"message": {"content": '{"value": "not-an-integer"}'}}
                ]
            }

    with pytest.raises(InvalidModelResponseError, match="invalid JSON after 1 attempts"):
        local_model_service.generate_structured_response(
            llm=FakeModel(),
            user_input="Return a value.",
            response_model=ExampleResponse,
            max_retries=0,
        )
