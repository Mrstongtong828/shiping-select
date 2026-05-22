from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from typing import Any

import httpx
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

from src.schema import SubtitlePayload, VideoRecord


LOGGER = logging.getLogger("video_finder")
YOUTUBE_SEARCH_API = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_API = "https://www.googleapis.com/youtube/v3/videos"


def _get_youtube_api_key() -> str:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 YOUTUBE_API_KEY，请先在 .env 中配置")
    return api_key


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
        languages = ["zh-Hans", "zh-CN", "zh", "en"]
        transcript = YouTubeTranscriptApi().fetch(video_id, languages=languages)
        text = TextFormatter().format_transcript(transcript)[:subtitle_limit]
        return SubtitlePayload(
            text=text,
            language=getattr(transcript, "language_code", ""),
            source="youtube_transcript",
        )
    except Exception:
        LOGGER.warning("YouTube 字幕抓取失败: video_id=%s", video_id)
        return SubtitlePayload()


def _build_records_from_responses(
    search_items: list[dict[str, Any]],
    detail_items: list[dict[str, Any]],
    subtitle_limit: int,
    fetch_transcript: Callable[[str, int], SubtitlePayload] = _fetch_transcript,
) -> list[VideoRecord]:
    detail_map = {item["id"]: item for item in detail_items if item.get("id")}

    results: list[VideoRecord] = []
    for search_item in search_items:
        video_id = search_item.get("id", {}).get("videoId")
        if not video_id:
            continue
        detail = detail_map.get(video_id, {})
        snippet = detail.get("snippet", search_item.get("snippet", {}))
        statistics = detail.get("statistics", {})
        content = detail.get("contentDetails", {})
        subtitle = fetch_transcript(video_id, subtitle_limit)
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


def _search_sync(topic: str, limit: int, subtitle_limit: int) -> list[VideoRecord]:
    api_key = _get_youtube_api_key()
    timeout = httpx.Timeout(30.0)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            search_response = client.get(
                YOUTUBE_SEARCH_API,
                params={
                    "key": api_key,
                    "q": topic,
                    "part": "snippet",
                    "type": "video",
                    "maxResults": max(limit, 1),
                    "relevanceLanguage": "zh-CN",
                    "safeSearch": "none",
                },
            )
            search_response.raise_for_status()
            search_payload = search_response.json()
            items = search_payload.get("items", [])
            video_ids = [item["id"]["videoId"] for item in items if item.get("id", {}).get("videoId")]
            if not video_ids:
                return []

            detail_response = client.get(
                YOUTUBE_VIDEOS_API,
                params={
                    "key": api_key,
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids),
                },
            )
            detail_response.raise_for_status()
            detail_payload = detail_response.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:300]
        raise RuntimeError(f"YouTube API 调用失败: status={exc.response.status_code} body={body}") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"YouTube API 网络请求失败: {exc}") from exc

    return _build_records_from_responses(
        items,
        detail_payload.get("items", []),
        subtitle_limit,
        _fetch_transcript,
    )


async def search_youtube_videos(topic: str, limit: int = 15, subtitle_limit: int = 6000) -> list[VideoRecord]:
    return await asyncio.to_thread(_search_sync, topic, limit, subtitle_limit)
