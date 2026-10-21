"""Domain models. Keep discovery evidence separate from verification conclusions."""

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Voice(StrEnum):
    SOPRANO = "soprano"
    ALTO = "alto"
    TENOR = "tenor"
    BASS = "bass"
    UNKNOWN = "unknown"


class MaterialType(StrEnum):
    INDIVIDUAL_PART = "individual_part"
    SECTIONAL_REHEARSAL = "sectional_rehearsal"
    FULL_PERFORMANCE = "full_performance"
    ACCOMPANIMENT = "accompaniment"
    UNKNOWN = "unknown"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class WorkRecord(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    work_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    composers: list[str] = Field(default_factory=list)
    alternate_titles: list[str] = Field(default_factory=list)
    catalog_numbers: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    formation: str | None = None


class YouTubeCandidate(BaseModel):
    video_id: str = Field(min_length=1)
    url: HttpUrl
    title: str
    channel_title: str = ""
    description: str = ""
    published_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    work_id: str | None = None
    query: str = ""
    voice_guess: Voice = Voice.UNKNOWN
    material_type: MaterialType = MaterialType.UNKNOWN
    review_status: ReviewStatus = ReviewStatus.PENDING
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    discovered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
