import os
from dotenv import load_dotenv

from google import genai
from google.genai import types
from pydantic import BaseModel

from narrative_engine.config import GEMINI_MODEL
from narrative_engine.exceptions import OuterAPIError


def generate_structured_response[T: BaseModel](
    prompt: str,
    response_model: type[T],
) -> T:
    load_dotenv()

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=GEMINI_API_KEY)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=response_model.model_json_schema(),
        ),
    )
    if not response.text:
        raise OuterAPIError("Gemini Response is empty")
    return response_model.model_validate_json(response.text)