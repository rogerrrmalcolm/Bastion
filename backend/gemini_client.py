from pathlib import Path
import time
from collections.abc import Callable
from typing import TypeVar

from dotenv import load_dotenv
from google import genai
from google.genai import errors
import httpx
from pydantic import BaseModel

DEFAULT_MODEL = "gemini-2.5-flash"
MAX_RETRY_ATTEMPTS = 5
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

client = genai.Client()
StructuredResponse = TypeVar("StructuredResponse", bound=BaseModel)
GeminiResponse = TypeVar("GeminiResponse")


def _with_gemini_retries(operation: Callable[[], GeminiResponse]) -> GeminiResponse:
    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        try:
            return operation()
        except errors.APIError as error:
            status_code = getattr(error, "status_code", None)
            if attempt == MAX_RETRY_ATTEMPTS or status_code not in RETRY_STATUS_CODES:
                raise
            time.sleep(2 ** (attempt - 1))
        except httpx.TransportError:
            if attempt == MAX_RETRY_ATTEMPTS:
                raise
            time.sleep(2 ** (attempt - 1))

    raise RuntimeError("Gemini request retry loop exited unexpectedly.")


def _generate_content(
    model: str,
    contents: str,
    config: dict[str, object] | None = None,
):
    request = {
        "model": model,
        "contents": contents,
    }
    if config is not None:
        request["config"] = config

    return _with_gemini_retries(lambda: client.models.generate_content(**request))


def call_gemini(prompt: str, model: str = DEFAULT_MODEL) -> str:
    response = _generate_content(model=model, contents=prompt)
    return response.text or ""


def call_gemini_structured(
    prompt: str,
    response_model: type[StructuredResponse],
    model: str = DEFAULT_MODEL,
) -> StructuredResponse:
    response = _generate_content(
        model=model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": response_model.model_json_schema(),
        },
    )

    return response_model.model_validate_json(response.text or "{}")
