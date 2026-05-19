import json
import os
from pathlib import Path
import tempfile
import time
from collections.abc import Callable
from typing import TypeVar

from dotenv import load_dotenv
from google import genai
from google.genai import errors
import httpx
from pydantic import BaseModel

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.15
MAX_RETRY_ATTEMPTS = 5
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
DEFAULT_SYSTEM_INSTRUCTION = """
You are Bastion, an M&A diligence assistant. Be concise, data-first, and
evidence-disciplined. Prioritize numbers, periods, source labels, citations,
deal impact, and missing data over broad narrative. Do not invent financials,
market facts, sources, dates, risks, or valuation conclusions. If evidence is
missing, say exactly what is missing and why it matters. Keep prose fields short
and decision-oriented; use lists only for the most material items.
"""

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _configure_google_credentials() -> None:
    credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not credentials_json or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return

    credentials_path = Path(tempfile.gettempdir()) / "bastion-google-credentials.json"
    credentials = json.loads(credentials_json)
    credentials_path.write_text(json.dumps(credentials), encoding="utf-8")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)


_configure_google_credentials()

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
    generation_config: dict[str, object] = {
        "system_instruction": DEFAULT_SYSTEM_INSTRUCTION,
    }
    if not model.startswith("gemini-3"):
        generation_config["temperature"] = DEFAULT_TEMPERATURE
    if config is not None:
        generation_config.update(config)

    request = {
        "model": model,
        "contents": contents,
        "config": generation_config,
    }

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
