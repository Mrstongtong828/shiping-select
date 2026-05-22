from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from src.schema import SubtitlePayload, VideoRecord


BILIBILI_SEARCH_API = "https://api.bilibili.com/x/web-interface/search/type"
BILIBILI_VIEW_API = "https://api.bilibili.com/x/web-interface/view"
BILIBILI_PLAYER_API = "https://api.bilibili.com/x/player/v2"
LOGGER = logging.getLogger("video_finder")


def _strip_html(text: str) -> str:
    return (
        text.replace("<em class=\"keyword\">", "")
        .replace("</em>", "")
        .replace("&quot;", "\"")
        .replace("&amp;", "&")
    )


def _parse_duration(value: str) -> int:
    parts = [int(part) for part in value.split(":") if part.isdigit()]
    total = 0
    for part in parts:
        total = total * 60 + part
    return total


def _format_publish_time(timestamp: int | None) -> str:
    if not timestamp:
        return ""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone().isoformat()


async def _fetch_json(client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> dict[str, Any]:
    response = await client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") not in (0, None):
        raise RuntimeError(f"Bilibili API error: {payload.get('message') or payload.get('code')}")
    return payload


async def _fetch_subtitle(
    client: httpx.AsyncClient,
    *,
    aid: int,
    bvid: str,
    cid: int,
    subtitle_limit: int,
) -> SubtitlePayload:
    payload = await _fetch_json(client, BILIBILI_PLAYER_API, {"aid": aid, "bvid": bvid, "cid": cid})
    subtitle_info = payload.get("data", {}).get("subtitle", {})
    subtitle_list = subtitle_info.get("subtitles") or []
    if not subtitle_list:
        return SubtitlePayload()

    first = subtitle_list[0]
    subtitle_url = first.get("subtitle_url", "")
    if not subtitle_url:
        return SubtitlePayload()
    if subtitle_url.startswith("//"):
        subtitle_url = f"https:{subtitle_url}"

    response = await client.get(subtitle_url)
    response.raise_for_status()
    subtitle_payload = response.json()
    lines = subtitle_payload.get("body", [])
    text = "\n".join(item.get("content", "").strip() for item in lines if item.get("content"))
    return SubtitlePayload(
        text=text[:subtitle_limit],
        language=first.get("lan_doc") or first.get("lan", ""),
        source="bilibili_cc",
    )


async def _build_record(
    client: httpx.AsyncClient,
    *,
    item: dict[str, Any],
    subtitle_limit: int,
) -> VideoRecord:
    bvid = item.get("bvid", "")
    view_payload = await _fetch_json(client, BILIBILI_VIEW_API, {"bvid": bvid})
    data = view_payload.get("data", {})
    pages = data.get("pages") or []
    cid = pages[0].get("cid") if pages else item.get("cid", 0)
    subtitle = SubtitlePayload()
    if cid:
        try:
            subtitle = await _fetch_subtitle(
                client,
                aid=data.get("aid", 0),
                bvid=bvid,
                cid=cid,
                subtitle_limit=subtitle_limit,
            )
        except Exception:
            LOGGER.warning("B站字幕抓取失败: bvid=%s cid=%s", bvid, cid)
            subtitle = SubtitlePayload()

    stat = data.get("stat", {})
    owner = data.get("owner", {})
    return VideoRecord(
        platform="bilibili",
        video_id=bvid,
        title=_strip_html(item.get("title", data.get("title", ""))),
        url=f"https://www.bilibili.com/video/{bvid}",
        author=owner.get("name", item.get("author", "")),
        view=int(stat.get("view", 0) or 0),
        like=int(stat.get("like", 0) or 0),
        duration=int(data.get("duration", _parse_duration(item.get("duration", "0"))) or 0),
        publish_time=_format_publish_time(data.get("pubdate")),
        description=data.get("desc", ""),
        has_subtitle=bool(subtitle.text),
        subtitle_text=subtitle.text,
        subtitle_language=subtitle.language,
        subtitle_source=subtitle.source,
    )


async def search_bilibili_videos(topic: str, limit: int = 15, subtitle_limit: int = 6000) -> list[VideoRecord]:
    params = {
        "keyword": topic,
        "search_type": "video",
        "page": 1,
        "page_size": max(limit, 1),
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.bilibili.com/",
    }
    async with httpx.AsyncClient(headers=headers, timeout=20.0, follow_redirects=True) as client:
        payload = await _fetch_json(client, BILIBILI_SEARCH_API, params)
        items = payload.get("data", {}).get("result") or []
        selected = items[:limit]
        tasks = [_build_record(client, item=item, subtitle_limit=subtitle_limit) for item in selected if item.get("bvid")]
        if not tasks:
            return []
        results = await asyncio.gather(*tasks, return_exceptions=True)
        records: list[VideoRecord] = []
        for result in results:
            if isinstance(result, Exception):
                LOGGER.warning("B站单条视频处理失败: %s", result)
                continue
            records.append(result)
        return records
