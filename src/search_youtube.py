from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

from src.schema import SubtitlePayload, VideoRecord


LOGGER = logging.getLogger("video_finder")


def _build_youtube_client() -> Any:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 YOUTUBE_API_KEY，请先在 .env 中配置")
    return build("youtube", "v3", developerKey=api_key)


def _parse_duration(iso_duration: str) -> int:
    hours = minutes = seconds = 0
    buffer = ""
    for char in iso_duration.replace("PT", ""):
        if char.isdigit():
            buffer += char
            continue
        if char == "H":
            hours = int(buffer or "0")
        elif char == "M":
            minutes = int(buffer or "0")
        elif char == "S":
            seconds = int(buffer or "0")
        buffer = ""
    return hours * 3600 + minutes * 60 + seconds


def _fetch_transcript(video_id: str, subtitle_limit: int) -> SubtitlePayload:
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = None
        for languages in (["zh-Hans", "zh-CN", "zh", "en"],):
            try:
                transcript = transcript_list.find_transcript(languages)
                break
            except Exception:
                continue
        if transcript is None:
            transcript = transcript_list.find_generated_transcript(["zh-Hans", "zh", "en"])
        data = transcript.fetch()
        text = TextFormatter().format_transcript(data)[:subtitle_limit]
        return SubtitlePayload(
            text=text,
            language=transcript.language_code,
            source="youtube_transcript",
        )
    except Exception:
        LOGGER.warning("YouTube 字幕抓取失败: video_id=%s", video_id)
        return SubtitlePayload()


def _search_sync(topic: str, limit: int, subtitle_limit: int) -> list[VideoRecord]:
    youtube = _build_youtube_client()
    try:
        search_response = (
            youtube.search()
            .list(
                q=topic,
                part="snippet",
                type="video",
                maxResults=max(limit, 1),
                relevanceLanguage="zh-CN",
                safeSearch="none",
            )
            .execute()
        )
    except HttpError as exc:
        raise RuntimeError(f"YouTube search API 调用失败: {exc}") from exc

    items = search_response.get("items", [])
    video_ids = [item["id"]["videoId"] for item in items if item.get("id", {}).get("videoId")]
    if not video_ids:
        return []

    video_response = (
        youtube.videos()
        .list(part="snippet,statistics,contentDetails", id=",".join(video_ids))
        .execute()
    )
    detail_map = {item["id"]: item for item in video_response.get("items", [])}

    results: list[VideoRecord] = []
    for search_item in items:
        video_id = search_item.get("id", {}).get("videoId")
        if not video_id:
            continue
        detail = detail_map.get(video_id, {})
        snippet = detail.get("snippet", search_item.get("snippet", {}))
        statistics = detail.get("statistics", {})
        content = detail.get("contentDetails", {})
        subtitle = _fetch_transcript(video_id, subtitle_limit)
        results.append(
            VideoRecord(
                platform="youtube",
                video_id=video_id,
                title=snippet.get("title", ""),
                url=f"https://www.youtube.com/watch?v={video_id}",
                author=snippet.get("channelTitle", ""),
                view=int(statistics.get("viewCount", 0) or 0),
                like=int(statistics.get("likeCount", 0) or 0),
                duration=_parse_duration(content.get("duration", "PT0S")),
                publish_time=snippet.get("publishedAt", ""),
                description=snippet.get("description", ""),
                has_subtitle=bool(subtitle.text),
                subtitle_text=subtitle.text,
                subtitle_language=subtitle.language,
                subtitle_source=subtitle.source,
            )
        )
    return results


async def search_youtube_videos(topic: str, limit: int = 15, subtitle_limit: int = 6000) -> list[VideoRecord]:
    return await asyncio.to_thread(_search_sync, topic, limit, subtitle_limit)
