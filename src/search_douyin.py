from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from typing import Any

import httpx

from src.schema import VideoRecord

LOGGER = logging.getLogger("video_finder")
DEFAULT_REFERENCE_JSON = Path("douyinpachong-main") / "foshan_hot_videos.json"
DEFAULT_EXTERNAL_API_BASE = "http://127.0.0.1:5555"
EXTERNAL_SEARCH_PATH = "/douyin/search/video"


def _pick_first(*values: object) -> str:
    for value in values:
        if value is not None and str(value).strip():
            return " ".join(str(value).split())
    return ""


def _parse_count(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value or "").strip().replace(",", "")
    if not text:
        return 0
    multipliers = {"万": 10_000, "w": 10_000, "W": 10_000}
    suffix = text[-1]
    if suffix in multipliers:
        try:
            return int(float(text[:-1]) * multipliers[suffix])
        except ValueError:
            return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def _load_reference_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Douyin reference JSON not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_video_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("视频列表", "videos", "items", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _iter_external_video_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ("data", "result", "results", "items", "videos", "aweme_list"):
        value = payload.get(key)
        if isinstance(value, list):
            flattened: list[dict[str, Any]] = []
            for item in value:
                if isinstance(item, dict):
                    flattened.append(item)
                elif isinstance(item, list):
                    flattened.extend(nested for nested in item if isinstance(nested, dict))
            return flattened
        if isinstance(value, dict):
            nested = _iter_external_video_items(value)
            if nested:
                return nested
    return []


def _author_name(item: dict[str, Any]) -> str:
    author = item.get("author")
    if isinstance(author, dict):
        return _pick_first(author.get("nickname"), author.get("name"), author.get("unique_id"))
    return _pick_first(author, item.get("nickname"), item.get("author_name"))


def _publish_time(value: object) -> str:
    if isinstance(value, int | float) and value > 0:
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    return _pick_first(value)


def _video_url(item: dict[str, Any], video_id: str) -> str:
    share_info = item.get("share_info")
    share_url = share_info.get("share_url") if isinstance(share_info, dict) else ""
    return _pick_first(
        item.get("share_url"),
        item.get("url"),
        item.get("video_url"),
        share_url,
        f"https://www.douyin.com/video/{video_id}" if video_id else "",
    )


def build_douyin_records_from_external_payload(payload: Any, *, limit: int) -> list[VideoRecord]:
    """Convert TikTokDownloader/Douyin Web API search results into unified video records."""
    records: list[VideoRecord] = []
    for index, item in enumerate(_iter_external_video_items(payload)):
        if len(records) >= limit:
            break
        video_id = _pick_first(item.get("aweme_id"), item.get("id"), item.get("item_id"), item.get("video_id"))
        statistics = item.get("statistics") if isinstance(item.get("statistics"), dict) else {}
        title = _pick_first(item.get("desc"), item.get("title"), item.get("caption"), f"douyin-{index + 1}")
        url = _video_url(item, video_id)
        records.append(
            VideoRecord(
                platform="douyin",
                video_id=video_id or url or f"douyin-{index + 1}",
                title=title,
                url=url or f"https://www.douyin.com/search/{title}",
                author=_author_name(item),
                view=_parse_count(item.get("view") or item.get("play_count") or statistics.get("play_count")),
                like=_parse_count(
                    item.get("digg_count")
                    or item.get("like")
                    or item.get("like_count")
                    or statistics.get("digg_count")
                    or statistics.get("like_count")
                ),
                duration=_parse_count(item.get("duration")),
                publish_time=_publish_time(item.get("create_time") or item.get("publish_time")),
                description=title,
                has_subtitle=False,
                subtitle_source="external_api",
            )
        )
    return records


def build_douyin_records_from_payload(payload: dict[str, Any], *, limit: int) -> list[VideoRecord]:
    """Convert the reference crawler JSON shape into unified video records."""
    records: list[VideoRecord] = []
    for index, item in enumerate(_iter_video_items(payload)):
        if len(records) >= limit:
            break
        url = _pick_first(item.get("官网链接"), item.get("url"), item.get("share_url"), item.get("链接"))
        title = _pick_first(item.get("标题"), item.get("title"), item.get("desc"), "无标题")
        video_id = _pick_first(item.get("aweme_id"), item.get("id"), item.get("视频ID"), url, f"douyin-{index + 1}")
        author = _pick_first(item.get("作者"), item.get("author"), item.get("nickname"))
        records.append(
            VideoRecord(
                platform="douyin",
                video_id=video_id,
                title=title,
                url=url or f"https://www.douyin.com/search/{payload.get('搜索关键词', '')}",
                author=author,
                view=_parse_count(item.get("播放数") or item.get("播放量") or item.get("view")),
                like=_parse_count(item.get("点赞数") or item.get("like") or item.get("digg_count")),
                description=title,
                has_subtitle=False,
                subtitle_source="",
            )
        )
    return records


def _load_reference_records(limit: int) -> list[VideoRecord]:
    configured_path = os.getenv("DOUYIN_SAMPLE_JSON", "").strip()
    path = Path(configured_path) if configured_path else DEFAULT_REFERENCE_JSON
    payload = _load_reference_payload(path)
    records = build_douyin_records_from_payload(payload, limit=limit)
    LOGGER.info("Douyin reference records loaded: path=%s count=%s", path, len(records))
    return records


def _external_api_enabled() -> bool:
    return os.getenv("DOUYIN_SEARCH_MODE", "").strip().lower() in {"external_api", "api", "realtime"}


async def _search_with_external_api(topic: str, limit: int) -> list[VideoRecord]:
    base_url = os.getenv("DOUYIN_EXTERNAL_API_BASE", DEFAULT_EXTERNAL_API_BASE).strip().rstrip("/")
    url = f"{base_url}{EXTERNAL_SEARCH_PATH}"
    headers: dict[str, str] = {}
    token = os.getenv("DOUYIN_EXTERNAL_API_TOKEN", "").strip()
    if token:
        headers["token"] = token

    payload = {
        "keyword": topic,
        "pages": max(1, ceil(limit / 20)),
        "channel": 1,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, json=payload, headers=headers or None)
        response.raise_for_status()
        records = build_douyin_records_from_external_payload(response.json(), limit=limit)
        if not records:
            raise ValueError("Douyin external API returned no video records")
        LOGGER.info("Douyin external API records loaded: topic=%s url=%s count=%s", topic, url, len(records))
        return records


async def search_douyin_videos(
    topic: str,
    limit: int = 10,
    subtitle_limit: int = 6000,
    enable_asr: bool = False,
    use_cache: bool = True,
) -> list[VideoRecord]:
    """Load Douyin reference crawler output and expose it through the main pipeline.

    The real Douyin crawler in `douyinpachong-main/` requires an interactive browser login,
    so the main pipeline reads an exported JSON file instead of launching a browser.
    Set `DOUYIN_SAMPLE_JSON` to point at a fresh crawler export for the current topic.
    """
    del subtitle_limit, enable_asr, use_cache
    if _external_api_enabled():
        try:
            return await _search_with_external_api(topic, limit)
        except Exception as exc:
            LOGGER.warning("Douyin external API failed, fallback to reference JSON: %s", exc)
    return _load_reference_records(limit)
