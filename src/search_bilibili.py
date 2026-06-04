from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from bilibili_api import search, video

from src.asr_whisper import fill_record_subtitle_with_asr
from src.cache_utils import build_cache_key, load_json_cache, save_json_cache
from src.schema import SubtitlePayload, VideoRecord

BILIBILI_PLAYER_API = "https://api.bilibili.com/x/player/v2"
LOGGER = logging.getLogger("video_finder")


def _build_credential():
    sessdata = os.getenv("BILI_SESSDATA")
    bili_jct = os.getenv("BILI_JCT")
    buvid3 = os.getenv("BILI_BUVID3")
    dedeuserid = os.getenv("BILI_DEDEUSERID")
    if not sessdata:
        return None
    try:
        from bilibili_api import Credential
    except ImportError:
        return None
    return Credential(
        sessdata=sessdata,
        bili_jct=bili_jct,
        buvid3=buvid3,
        dedeuserid=dedeuserid,
    )


def _strip_html(text: str) -> str:
    return text.replace('<em class="keyword">', "").replace("</em>", "").replace("&quot;", '"').replace("&amp;", "&")


def _parse_duration(value: str | int) -> int:
    if isinstance(value, int):
        return value
    parts = [int(part) for part in value.split(":") if part.isdigit()]
    total = 0
    for part in parts:
        total = total * 60 + part
    return total


def _format_publish_time(timestamp: int | None) -> str:
    if not timestamp:
        return ""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone().isoformat()


async def _fetch_public_player_subtitle(
    client: httpx.AsyncClient,
    *,
    aid: int,
    bvid: str,
    cid: int,
) -> dict[str, Any]:
    response = await client.get(
        BILIBILI_PLAYER_API,
        params={"aid": aid, "bvid": bvid, "cid": cid},
        timeout=20.0,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") not in (0, None):
        raise RuntimeError(f"Bilibili player API error: {payload.get('message') or payload.get('code')}")
    return payload.get("data", {}).get("subtitle", {})


def _subtitle_cache_key(bvid: str, cid: int, subtitle_limit: int) -> str:
    return build_cache_key("bilibili_subtitle", bvid, cid, subtitle_limit)


async def _download_subtitle_from_url(
    client: httpx.AsyncClient,
    subtitle_url: str,
    language: str,
    subtitle_limit: int,
) -> SubtitlePayload:
    if subtitle_url.startswith("//"):
        subtitle_url = f"https:{subtitle_url}"
    response = await client.get(subtitle_url, timeout=20.0)
    response.raise_for_status()
    payload = response.json()
    lines = payload.get("body", [])
    text = "\n".join(item.get("content", "").strip() for item in lines if item.get("content"))
    return SubtitlePayload(
        text=text[:subtitle_limit],
        language=language,
        source="bilibili_cc",
    )


async def _fetch_subtitle(
    client: httpx.AsyncClient,
    *,
    sdk_video: video.Video,
    aid: int,
    bvid: str,
    cid: int,
    info: dict[str, Any],
    subtitle_limit: int,
    use_cache: bool,
) -> SubtitlePayload:
    cache_key = _subtitle_cache_key(bvid, cid, subtitle_limit)
    if use_cache:
        cached = load_json_cache("subtitles_bilibili", cache_key)
        if cached is not None:
            LOGGER.info("Bilibili subtitle cache hit: bvid=%s cid=%s", bvid, cid)
            return SubtitlePayload.model_validate(cached)

    subtitle_meta = info.get("subtitle", {}) or {}
    subtitle_list = subtitle_meta.get("list") or []

    if not subtitle_list:
        try:
            player_subtitle = await _fetch_public_player_subtitle(client, aid=aid, bvid=bvid, cid=cid)
            subtitle_list = player_subtitle.get("subtitles") or []
        except Exception as exc:
            LOGGER.warning("Bilibili public subtitle metadata fetch failed: bvid=%s cid=%s error=%s", bvid, cid, exc)

    if not subtitle_list:
        credential = getattr(sdk_video, "credential", None)
        if credential is not None and getattr(credential, "sessdata", None):
            try:
                sdk_subtitle = await sdk_video.get_subtitle(cid=cid)
                subtitle_list = sdk_subtitle.get("subtitles") or sdk_subtitle.get("list") or []
            except Exception as exc:
                LOGGER.warning("Bilibili SDK subtitle metadata fetch failed: bvid=%s cid=%s error=%s", bvid, cid, exc)

    if not subtitle_list:
        return SubtitlePayload()

    first = subtitle_list[0]
    subtitle_url = first.get("subtitle_url", "")
    if not subtitle_url:
        return SubtitlePayload()

    result = await _download_subtitle_from_url(
        client,
        subtitle_url=subtitle_url,
        language=first.get("lan_doc") or first.get("lan", ""),
        subtitle_limit=subtitle_limit,
    )
    if use_cache and result.text:
        save_json_cache("subtitles_bilibili", cache_key, result.model_dump())
    return result


def _load_asr_subtitle_cache(record: VideoRecord, subtitle_limit: int) -> SubtitlePayload | None:
    cache_key = build_cache_key("bilibili_asr_subtitle", record.video_id, subtitle_limit)
    cached = load_json_cache("subtitles_bilibili", cache_key)
    if cached is None:
        return None
    LOGGER.info("Bilibili ASR subtitle cache hit: bvid=%s", record.video_id)
    return SubtitlePayload.model_validate(cached)


def _save_asr_subtitle_cache(record: VideoRecord, subtitle_limit: int) -> None:
    if not record.subtitle_text:
        return
    cache_key = build_cache_key("bilibili_asr_subtitle", record.video_id, subtitle_limit)
    save_json_cache(
        "subtitles_bilibili",
        cache_key,
        SubtitlePayload(
            text=record.subtitle_text,
            language=record.subtitle_language,
            source=record.subtitle_source,
        ).model_dump(),
    )


async def _build_record(
    client: httpx.AsyncClient,
    *,
    item: dict[str, Any],
    subtitle_limit: int,
    enable_asr: bool,
    use_cache: bool,
) -> VideoRecord:
    bvid = item.get("bvid", "")
    credential = _build_credential()
    sdk_video = video.Video(bvid=bvid, credential=credential)

    info = await sdk_video.get_info()
    pages = await sdk_video.get_pages()
    first_page = pages[0] if pages else {}
    cid = first_page.get("cid") or info.get("cid")

    subtitle = SubtitlePayload()
    if cid:
        try:
            subtitle = await _fetch_subtitle(
                client,
                sdk_video=sdk_video,
                aid=info.get("aid", 0),
                bvid=bvid,
                cid=cid,
                info=info,
                subtitle_limit=subtitle_limit,
                use_cache=use_cache,
            )
        except Exception as exc:
            LOGGER.warning("Bilibili subtitle fetch failed: bvid=%s cid=%s error=%s", bvid, cid, exc)

    stat = info.get("stat", {})
    owner = info.get("owner", {})
    record = VideoRecord(
        platform="bilibili",
        video_id=bvid,
        title=_strip_html(item.get("title", info.get("title", ""))),
        url=item.get("arcurl") or item.get("url") or f"https://www.bilibili.com/video/{bvid}",
        author=owner.get("name", item.get("author", "")),
        view=int(stat.get("view", item.get("play", 0)) or 0),
        like=int(stat.get("like", item.get("like", 0)) or 0),
        duration=int(info.get("duration", _parse_duration(item.get("duration", "0"))) or 0),
        publish_time=_format_publish_time(info.get("pubdate")),
        description=info.get("desc", item.get("description", "")),
        has_subtitle=bool(subtitle.text),
        subtitle_text=subtitle.text,
        subtitle_language=subtitle.language,
        subtitle_source=subtitle.source,
    )

    if enable_asr and not record.has_subtitle:
        cached_asr = _load_asr_subtitle_cache(record, subtitle_limit) if use_cache else None
        if cached_asr and cached_asr.text:
            record = record.model_copy(
                update={
                    "has_subtitle": True,
                    "subtitle_text": cached_asr.text,
                    "subtitle_language": cached_asr.language,
                    "subtitle_source": cached_asr.source,
                }
            )
        else:
            try:
                record = await fill_record_subtitle_with_asr(record, subtitle_limit=subtitle_limit)
                if use_cache and record.has_subtitle:
                    _save_asr_subtitle_cache(record, subtitle_limit)
            except Exception as exc:
                LOGGER.warning("Bilibili ASR fallback failed: bvid=%s error=%s", bvid, exc)
    return record


async def search_bilibili_videos(
    topic: str,
    limit: int = 15,
    subtitle_limit: int = 6000,
    enable_asr: bool = False,
    use_cache: bool = True,
) -> list[VideoRecord]:
    search_payload = await search.search_by_type(
        topic,
        search_type=search.SearchObjectType.VIDEO,
        order_type=search.OrderVideo.TOTALRANK,
        page=1,
        page_size=max(limit, 1),
    )
    items = search_payload.get("result") or []
    selected = items[:limit]

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.bilibili.com/",
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=20.0) as client:
        tasks = [
            _build_record(
                client,
                item=item,
                subtitle_limit=subtitle_limit,
                enable_asr=enable_asr,
                use_cache=use_cache,
            )
            for item in selected
            if item.get("bvid")
        ]
        if not tasks:
            return []
        results = await asyncio.gather(*tasks, return_exceptions=True)
        records: list[VideoRecord] = []
        for result in results:
            if isinstance(result, Exception):
                LOGGER.warning("Bilibili single video processing failed: %s", result)
                continue
            records.append(result)
        return records
