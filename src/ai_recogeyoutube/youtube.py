"""Small official YouTube Data API v3 client; metadata only, no media downloads."""

from datetime import datetime
from typing import Any

import httpx

from .models import YouTubeCandidate

BASE_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeAPIError(RuntimeError):
    """Raised for API, quota, or transport failures."""


class YouTubeClient:
    def __init__(self, api_key: str, timeout: float = 20.0) -> None:
        if not api_key.strip():
            raise ValueError("YOUTUBE_API_KEY is not configured")
        self._api_key = api_key
        self._timeout = timeout

    def search_videos(self, query: str, max_results: int = 25) -> list[YouTubeCandidate]:
        """Search public video metadata and return normalized candidates."""
        max_results = min(max(max_results, 1), 50)
        params = {
            "part": "snippet",
            "type": "video",
            "q": query,
            "maxResults": max_results,
            "key": self._api_key,
        }
        try:
            response = httpx.get(
                f"{BASE_URL}/search", params=params, timeout=self._timeout
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise YouTubeAPIError(f"YouTube search failed: {exc}") from exc

        candidates: list[YouTubeCandidate] = []
        for item in payload.get("items", []):
            video_id = (item.get("id") or {}).get("videoId")
            snippet = item.get("snippet") or {}
            if not video_id:
                continue
            published_at = None
            if snippet.get("publishedAt"):
                try:
                    published_at = datetime.fromisoformat(
                        snippet["publishedAt"].replace("Z", "+00:00")
                    )
                except ValueError:
                    pass
            candidates.append(
                YouTubeCandidate(
                    video_id=video_id,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    title=snippet.get("title", ""),
                    channel_title=snippet.get("channelTitle", ""),
                    description=snippet.get("description", ""),
                    published_at=published_at,
                    query=query,
                    evidence=["youtube_data_api_search_result"],
                )
            )
        return candidates
