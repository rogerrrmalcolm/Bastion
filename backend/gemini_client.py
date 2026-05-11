from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

DEFAULT_MODEL = "gemini-3-flash-preview"

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

client = genai.Client()
StructuredResponse = TypeVar("StructuredResponse", bound=BaseModel)


def call_gemini(prompt: str, model: str = DEFAULT_MODEL) -> str:
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text or ""


def call_gemini_structured(
    prompt: str,
    response_model: type[StructuredResponse],
    model: str = DEFAULT_MODEL,
) -> StructuredResponse:
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": response_model.model_json_schema(),
        },
    )

    return response_model.model_validate_json(response.text or "{}")
