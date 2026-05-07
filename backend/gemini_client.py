from pathlib import Path

from dotenv import load_dotenv
from google import genai


DEFAULT_MODEL = "gemini-2.5-flash"

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

client = genai.Client()


def call_gemini(prompt: str, model: str = DEFAULT_MODEL) -> str:
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text or ""
