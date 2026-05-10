from pydantic import BaseModel
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Settings(BaseModel):
    anakin_api_key: str = os.getenv("ANAKIN_API_KEY", "")
    anakin_base_url: str = os.getenv("ANAKIN_BASE_URL", "https://api.anakin.io/v1")
    anakin_country: str = os.getenv("ANAKIN_COUNTRY", "in")
    poll_interval_ms: int = int(os.getenv("ANAKIN_POLL_INTERVAL_MS", "3000"))
    poll_timeout_ms: int = int(os.getenv("ANAKIN_POLL_TIMEOUT_MS", "120000"))
    max_urls: int = int(os.getenv("MAX_TENDER_URLS", "10"))
    max_iterations: int = int(os.getenv("MAX_AGENT_ITERATIONS", "2"))

    # LLM filter (OpenRouter / OpenAI-compatible)
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    llm_model: str = os.getenv("LLM_MODEL", "openai/gpt-5.5")


settings = Settings()
