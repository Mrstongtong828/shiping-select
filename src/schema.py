from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


PlatformName = Literal["bilibili", "youtube"]
AudienceName = Literal["", "科普", "本科入门", "本科进阶", "研究生"]
RecommendName = Literal["", "yes", "no"]


class VideoRecord(BaseModel):
    platform: PlatformName
    video_id: str = Field(description="平台内视频唯一标识，例如 bvid 或 YouTube videoId")
    title: str
    url: str
    author: str = ""
    view: int = 0
    like: int = 0
    duration: int = Field(default=0, description="单位为秒")
    publish_time: str = ""
    description: str = ""
    has_subtitle: bool = False
    subtitle_text: str = ""
    subtitle_language: str = ""
    subtitle_source: str = ""
    relevance: int | None = None
    depth: int | None = None
    clarity: int | None = None
    audience: AudienceName = ""
    recommend: RecommendName = ""
    reason: str = ""


class SubtitlePayload(BaseModel):
    text: str = ""
    language: str = ""
    source: str = ""


class SearchSummary(BaseModel):
    total_records: int = 0
    subtitle_success_count: int = 0
    subtitle_success_ratio: float = 0.0
    errors: list[str] = Field(default_factory=list)
