import json
from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv
from google import genai 

DEFAULT_MODEL = "gemini-2.5-flash"

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

client = genai.Client()

StructuredResponse = TypeVar("StructuredResponse", bound=BaseModel)

_GEMINI_JSON_SCHEMA_KEYS = {
    "$id",
    "$defs",
    "$ref",
    "$anchor",
    "type",
    "format",
    "title",
    "description",
    "enum",
    "items",
    "prefixItems",
    "minItems",
    "maxItems",
    "minimum",
    "maximum",
    "anyOf",
    "oneOf",
    "properties",
    "additionalProperties",
    "required",
    "propertyOrdering",
}


def _clean_json_schema_for_gemini(schema: object) -> object:
    if isinstance(schema, list):
        return [_clean_json_schema_for_gemini(item) for item in schema]

    if not isinstance(schema, dict):
        return schema

    cleaned: dict[str, object] = {}
    for key, value in schema.items():
        if key not in _GEMINI_JSON_SCHEMA_KEYS:
            continue

        if key in {"properties", "$defs"} and isinstance(value, dict):
            cleaned[key] = {
                property_name: _clean_json_schema_for_gemini(property_schema)
                for property_name, property_schema in value.items()
            }
        else:
            cleaned[key] = _clean_json_schema_for_gemini(value)

    return cleaned


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
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=_clean_json_schema_for_gemini(
                response_model.model_json_schema()
            ),
            temperature=0.1,
        ),
    )

    raw_text = response.text or "{}"
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"Gemini returned invalid JSON: {raw_text}") from error

    try:
        return response_model.model_validate(payload)
    except ValidationError as error:
        raise ValueError(f"Gemini JSON did not match {response_model.__name__}") from error
