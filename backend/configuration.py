from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Keep committed defaults and remote credentials in .env, while allowing a
# gitignored local service stack to override only infrastructure endpoints.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env.services.local", override=True)
