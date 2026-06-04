from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

from src.asr_whisper import fill_record_subtitle_with_asr
from src.cache_utils import build_cache_key, load_json_cache, save_json_cache
from src.env_utils import is_real_env_value
from src.schema import SubtitlePayload, VideoRecord

LOGGER = logging.getLogger("video_finder")


def _build_youtube_client() -> Any:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not is_real_env_value(api_key):
        raise RuntimeError("Missing YOUTUBE_API_KEY. Please configure it in .env")
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


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _normalize_upload_date(value: Any) -> str:
    text = str(value or "")
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:]}T00:00:00Z"
    return text


def _extract_video_id(entry: dict[str, Any]) -> str:
    video_id = str(entry.get("id") or "").strip()
    if video_id:
        return video_id
    url = str(entry.get("webpage_url") or entry.get("url") or "")
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    return match.group(1) if match else ""


def _youtube_url(video_id: str, entry: dict[str, Any] | None = None) -> str:
    if entry:
        webpage_url = str(entry.get("webpage_url") or "")
        if webpage_url.startswith("http"):
            return webpage_url
    return f"https://www.youtube.com/watch?v={video_id}"


def _execute_with_retry(request, *, label: str, retries: int = 3) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            LOGGER.info("YouTube request start: %s attempt=%s", label, attempt)
            started = time.perf_counter()
            response = request.execute()
            elapsed = time.perf_counter() - started
            LOGGER.info("YouTube request success: %s attempt=%s elapsed=%.2fs", label, attempt, elapsed)
            return response
        except HttpError as exc:
            last_error = exc
            LOGGER.warning("YouTube request failed: %s attempt=%s error=%s", label, attempt, exc)
        except Exception as exc:
            last_error = exc
            LOGGER.warning("YouTube request failed: %s attempt=%s error=%s", label, attempt, exc)
        if attempt < retries:
            time.sleep(attempt)
    raise RuntimeError(f"YouTube request failed after retries for {label}: {last_error}")


def _subtitle_cache_key(video_id: str, subtitle_limit: int) -> str:
    return build_cache_key("youtube_subtitle", video_id, subtitle_limit)


def _asr_cache_key(video_id: str, subtitle_limit: int) -> str:
    return build_cache_key("youtube_asr_subtitle", video_id, subtitle_limit)


def _fetch_transcript(video_id: str, subtitle_limit: int, use_cache: bool) -> SubtitlePayload:
    cache_key = _subtitle_cache_key(video_id, subtitle_limit)
    if use_cache:
        cached = load_json_cache("subtitles_youtube", cache_key)
        if cached is not None:
            LOGGER.info("YouTube subtitle cache hit: video_id=%s", video_id)
            return SubtitlePayload.model_validate(cached)

    try:
        transcript_api = YouTubeTranscriptApi()
        transcript_list = transcript_api.list(video_id)
        transcript = None
        for languages in (["zh-Hans", "zh-CN", "zh", "en"],):
            try:
                transcript = transcript_list.find_transcript(languages)
                LOGGER.info("YouTube transcript found: video_id=%s language=%s", video_id, languages)
                break
            except Exception:
                continue
        if transcript is None:
            transcript = transcript_list.find_generated_transcript(["zh-Hans", "zh", "en"])
            LOGGER.info(
                "YouTube generated transcript used: video_id=%s language=%s", video_id, transcript.language_code
            )
        data = transcript.fetch()
        text = TextFormatter().format_transcript(data)[:subtitle_limit]
        result = SubtitlePayload(
            text=text,
            language=transcript.language_code,
            source="youtube_transcript",
        )
        if use_cache and result.text:
            save_json_cache("subtitles_youtube", cache_key, result.model_dump())
        return result
    except Exception as exc:
        LOGGER.warning("YouTube subtitle fetch failed: video_id=%s error=%s", video_id, exc)
        return SubtitlePayload()


def _load_asr_subtitle_cache(video_id: str, subtitle_limit: int) -> SubtitlePayload | None:
    cached = load_json_cache("subtitles_youtube", _asr_cache_key(video_id, subtitle_limit))
    if cached is None:
        return None
    LOGGER.info("YouTube ASR subtitle cache hit: video_id=%s", video_id)
    return SubtitlePayload.model_validate(cached)


def _save_asr_subtitle_cache(record: VideoRecord, subtitle_limit: int) -> None:
    if not record.subtitle_text:
        return
    save_json_cache(
        "subtitles_youtube",
        _asr_cache_key(record.video_id, subtitle_limit),
        SubtitlePayload(
            text=record.subtitle_text,
            language=record.subtitle_language,
            source=record.subtitle_source,
        ).model_dump(),
    )


def _attach_subtitle(
    record: VideoRecord,
    *,
    subtitle_limit: int,
    enable_asr: bool,
    use_cache: bool,
) -> VideoRecord:
    subtitle = _fetch_transcript(record.video_id, subtitle_limit, use_cache=use_cache)
    record = record.model_copy(
        update={
            "has_subtitle": bool(subtitle.text),
            "subtitle_text": subtitle.text,
            "subtitle_language": subtitle.language,
            "subtitle_source": subtitle.source,
        }
    )
    if enable_asr and not record.has_subtitle:
        cached_asr = _load_asr_subtitle_cache(record.video_id, subtitle_limit) if use_cache else None
        if cached_asr and cached_asr.text:
            return record.model_copy(
                update={
                    "has_subtitle": True,
                    "subtitle_text": cached_asr.text,
                    "subtitle_language": cached_asr.language,
                    "subtitle_source": cached_asr.source,
                }
            )
        try:
            LOGGER.info("YouTube ASR fallback start: video_id=%s", record.video_id)
            record = asyncio.run(fill_record_subtitle_with_asr(record, subtitle_limit=subtitle_limit))
            LOGGER.info("YouTube ASR fallback success: video_id=%s", record.video_id)
            if use_cache and record.has_subtitle:
                _save_asr_subtitle_cache(record, subtitle_limit)
        except Exception as exc:
            LOGGER.warning("YouTube ASR fallback failed: video_id=%s error=%s", record.video_id, exc)
    return record


def _search_with_data_api(
    topic: str,
    limit: int,
    subtitle_limit: int,
    enable_asr: bool,
    use_cache: bool,
) -> list[VideoRecord]:
    youtube = _build_youtube_client()
    search_request = youtube.search().list(
        q=topic,
        part="snippet",
        type="video",
        maxResults=max(limit, 1),
        relevanceLanguage="zh-CN",
        safeSearch="none",
    )
    search_response = _execute_with_retry(search_request, label=f"search:{topic}")

    items = search_response.get("items", [])
    video_ids = [item["id"]["videoId"] for item in items if item.get("id", {}).get("videoId")]
    if not video_ids:
        LOGGER.info("YouTube search returned no video ids for topic=%s", topic)
        return []

    video_request = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids),
    )
    video_response = _execute_with_retry(video_request, label=f"videos:{len(video_ids)}")
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
        record = VideoRecord(
            platform="youtube",
            video_id=video_id,
            title=snippet.get("title", ""),
            url=f"https://www.youtube.com/watch?v={video_id}",
            author=snippet.get("channelTitle", ""),
            view=_safe_int(statistics.get("viewCount")),
            like=_safe_int(statistics.get("likeCount")),
            duration=_parse_duration(content.get("duration", "PT0S")),
            publish_time=snippet.get("publishedAt", ""),
            description=snippet.get("description", ""),
        )
        results.append(
            _attach_subtitle(
                record,
                subtitle_limit=subtitle_limit,
                enable_asr=enable_asr,
                use_cache=use_cache,
            )
        )
    return results


def _search_with_ytdlp(
    topic: str,
    limit: int,
    subtitle_limit: int,
    enable_asr: bool,
    use_cache: bool,
) -> list[VideoRecord]:
    search_query = f"ytsearch{max(limit, 1)}:{topic}"
    options = {
        "extract_flat": "in_playlist",
        "ignoreerrors": True,
        "noplaylist": True,
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
    }
    LOGGER.info("YouTube yt-dlp fallback search start: query=%s", search_query)
    with YoutubeDL(options) as downloader:
        payload = downloader.extract_info(search_query, download=False)
    entries = (payload or {}).get("entries") or []

    results: list[VideoRecord] = []
    for entry in entries:
        if not entry:
            continue
        video_id = _extract_video_id(entry)
        if not video_id:
            LOGGER.warning("YouTube yt-dlp entry missing video id: title=%s", entry.get("title", ""))
            continue
        record = VideoRecord(
            platform="youtube",
            video_id=video_id,
            title=str(entry.get("title") or ""),
            url=_youtube_url(video_id, entry),
            author=str(entry.get("uploader") or entry.get("channel") or entry.get("channel_title") or ""),
            view=_safe_int(entry.get("view_count")),
            like=_safe_int(entry.get("like_count")),
            duration=_safe_int(entry.get("duration")),
            publish_time=_normalize_upload_date(entry.get("upload_date") or entry.get("release_date")),
            description=str(entry.get("description") or ""),
        )
        results.append(
            _attach_subtitle(
                record,
                subtitle_limit=subtitle_limit,
                enable_asr=enable_asr,
                use_cache=use_cache,
            )
        )
    LOGGER.info("YouTube yt-dlp fallback search finished with %s records", len(results))
    return results


def _search_sync(topic: str, limit: int, subtitle_limit: int, enable_asr: bool, use_cache: bool) -> list[VideoRecord]:
    if is_real_env_value(os.getenv("YOUTUBE_API_KEY")):
        try:
            return _search_with_data_api(topic, limit, subtitle_limit, enable_asr, use_cache)
        except Exception as exc:
            LOGGER.warning("YouTube Data API search failed; falling back to yt-dlp: %s", exc)
    else:
        LOGGER.warning("Missing YOUTUBE_API_KEY; falling back to yt-dlp YouTube search")
    return _search_with_ytdlp(topic, limit, subtitle_limit, enable_asr, use_cache)


async def search_youtube_videos(
    topic: str,
    limit: int = 15,
    subtitle_limit: int = 6000,
    enable_asr: bool = False,
    use_cache: bool = True,
) -> list[VideoRecord]:
    return await asyncio.to_thread(_search_sync, topic, limit, subtitle_limit, enable_asr, use_cache)
