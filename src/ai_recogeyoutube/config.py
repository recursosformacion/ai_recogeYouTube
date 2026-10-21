"""Application settings loaded from environment variables."""

from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
        self.db_path = Path(
            os.getenv("AI_YOUTUBE_DB_PATH", "./data/ai_recogeyoutube.sqlite3")
        )
        try:
            self.max_results = int(os.getenv("AI_YOUTUBE_MAX_RESULTS", "25"))
        except ValueError:
            self.max_results = 25
        self.max_results = min(max(self.max_results, 1), 50)


@lru_cache
def get_settings() -> Settings:
    return Settings()
