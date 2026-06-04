from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
from typing import Awaitable

from dotenv import load_dotenv

from src.cache_utils import build_cache_key, clear_cache, load_json_cache, save_json_cache
from src.evaluate import evaluate_records
from src.exporters import export_csv, export_json, export_markdown, export_run_log
from src.logging_utils import setup_logger
from src.schema import SearchSummary, VideoRecord
from src.search_bilibili import search_bilibili_videos
from src.search_douyin import search_douyin_videos
from src.search_youtube import search_youtube_videos

RESULTS_DIR = Path("results")
LOGGER = logging.getLogger("video_finder")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the video selection pipeline."""
    parser = argparse.ArgumentParser(description="Video learning resource finder")
    parser.add_argument("--topic", required=True, help="Search topic, for example: PCA 主成分分析")
    parser.add_argument(
        "--platform",
        default="bilibili,youtube",
        help="Comma-separated platforms: bilibili,youtube,douyin or all",
    )
    parser.add_argument("--max", type=int, default=30, help="Max number of returned videos")
    parser.add_argument(
        "--subtitle-limit",
        type=int,
        default=6000,
        help="Max subtitle characters kept for each video",
    )
    parser.add_argument(
        "--skip-evaluate",
        action="store_true",
        help="Skip the LLM evaluation stage",
    )
    parser.add_argument(
        "--enable-asr",
        action="store_true",
        help="Enable yt-dlp + faster-whisper fallback for videos without subtitles",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable reading and writing local cache for this run",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear local cache before running",
    )
    return parser


def normalize_platforms(platforms: list[str]) -> list[str]:
    """Normalize platform CLI values and expand the all shortcut."""
    platform_list = [item.strip().lower() for item in platforms if item.strip()]
    if not platform_list:
        raise ValueError("At least one platform is required")
    if "all" in platform_list:
        platform_list = ["bilibili", "youtube", "douyin"]

    supported = {"bilibili", "youtube", "douyin"}
    unknown = sorted(set(platform_list) - supported)
    if unknown:
        raise ValueError(f"Unsupported platform(s): {', '.join(unknown)}")

    deduped: list[str] = []
    for platform_name in platform_list:
        if platform_name not in deduped:
            deduped.append(platform_name)
    return deduped


def slugify_topic(topic: str) -> str:
    """Convert a topic into a filesystem-safe result filename stem."""
    chars: list[str] = []
    for ch in topic:
        if ch.isalnum() or ch in {"_", "-", " "}:
            chars.append(ch)
        else:
            chars.append("_")
    return "".join(chars).strip().replace(" ", "_") or "results"


async def gather_records(
    topic: str,
    platforms: list[str],
    max_results: int,
    subtitle_limit: int,
    enable_asr: bool,
    use_cache: bool,
) -> tuple[list[VideoRecord], list[str]]:
    """Search configured platforms and merge their video records."""
    platform_list = normalize_platforms(platforms)

    per_platform = max(1, max_results // len(platform_list))
    coros: dict[str, Awaitable[list[VideoRecord]]] = {}

    if "bilibili" in platform_list:
        coros["bilibili"] = search_bilibili_videos(
            topic=topic,
            limit=per_platform,
            subtitle_limit=subtitle_limit,
            enable_asr=enable_asr,
            use_cache=use_cache,
        )
    if "youtube" in platform_list:
        coros["youtube"] = search_youtube_videos(
            topic=topic,
            limit=per_platform,
            subtitle_limit=subtitle_limit,
            enable_asr=enable_asr,
            use_cache=use_cache,
        )
    if "douyin" in platform_list:
        coros["douyin"] = search_douyin_videos(
            topic=topic,
            limit=per_platform,
            subtitle_limit=subtitle_limit,
            enable_asr=enable_asr,
            use_cache=use_cache,
        )

    merged: list[VideoRecord] = []
    errors: list[str] = []
    pending: list[tuple[str, Awaitable[list[VideoRecord]], str]] = []

    for platform_name, coro in coros.items():
        cache_key = build_cache_key(topic, platform_name, per_platform, subtitle_limit, enable_asr)
        if use_cache:
            cached = load_json_cache("searches", cache_key)
            if cached is not None:
                cached_records = [VideoRecord.model_validate(item) for item in cached]
                LOGGER.info("%s search cache hit with %s records", platform_name, len(cached_records))
                merged.extend(cached_records)
                continue
        pending.append((platform_name, coro, cache_key))

    if pending:
        results = await asyncio.gather(*(coro for _, coro, _ in pending), return_exceptions=True)
        for (platform_name, _, cache_key), batch in zip(pending, results):
            if isinstance(batch, Exception):
                message = f"{platform_name} search failed: {batch}"
                LOGGER.error(message)
                errors.append(message)
                continue
            LOGGER.info("%s search finished with %s records", platform_name, len(batch))
            if use_cache:
                save_json_cache("searches", cache_key, [record.model_dump() for record in batch])
            merged.extend(batch)

    return merged[:max_results], errors


def build_summary(records: list[VideoRecord], errors: list[str]) -> SearchSummary:
    """Build run-level metrics for exported logs and Markdown."""
    total_records = len(records)
    subtitle_success_count = 0
    evaluation_success_count = 0
    platform_counts: dict[str, int] = {}
    subtitle_source_counts: dict[str, int] = {}
    for record in records:
        platform_counts[record.platform] = platform_counts.get(record.platform, 0) + 1
        if record.has_subtitle:
            subtitle_success_count += 1
            source = record.subtitle_source or "unknown"
            subtitle_source_counts[source] = subtitle_source_counts.get(source, 0) + 1
        if record.recommend in {"yes", "no"}:
            evaluation_success_count += 1
    return SearchSummary(
        total_records=total_records,
        subtitle_success_count=subtitle_success_count,
        subtitle_success_ratio=subtitle_success_count / total_records if total_records else 0.0,
        evaluation_success_count=evaluation_success_count,
        evaluation_success_ratio=evaluation_success_count / total_records if total_records else 0.0,
        platform_counts=platform_counts,
        subtitle_source_counts=subtitle_source_counts,
        errors=errors,
    )


def export_results(topic: str, records: list[VideoRecord], summary: SearchSummary) -> dict[str, Path]:
    """Export all result formats for a finished run."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = slugify_topic(topic)
    csv_path = RESULTS_DIR / f"{stem}.csv"
    json_path = RESULTS_DIR / f"{stem}.json"
    md_path = RESULTS_DIR / f"{stem}.md"
    log_path = RESULTS_DIR / f"{stem}_run.log"

    export_csv(csv_path, records)
    export_json(json_path, records)
    export_markdown(md_path, topic, records, summary)
    export_run_log(log_path, topic, summary)
    return {"csv": csv_path, "json": json_path, "md": md_path, "log": log_path}


async def async_main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    setup_logger(RESULTS_DIR / "runtime.log")

    if args.clear_cache:
        clear_cache()
        LOGGER.info("Local cache cleared")

    platforms = [item.strip() for item in args.platform.split(",") if item.strip()]
    LOGGER.info(
        "Start topic=%s platforms=%s max=%s use_cache=%s",
        args.topic,
        ",".join(platforms),
        args.max,
        not args.no_cache,
    )

    records, errors = await gather_records(
        topic=args.topic,
        platforms=platforms,
        max_results=args.max,
        subtitle_limit=args.subtitle_limit,
        enable_asr=args.enable_asr,
        use_cache=not args.no_cache,
    )
    if not args.skip_evaluate:
        evaluated_records, evaluation_errors = await evaluate_records(
            args.topic,
            records,
            use_cache=not args.no_cache,
        )
        records = evaluated_records
        errors.extend(evaluation_errors)

    summary = build_summary(records, errors)
    exported = export_results(args.topic, records, summary)

    LOGGER.info(
        "Done total=%s subtitle_success=%s eval_success=%s",
        summary.total_records,
        summary.subtitle_success_count,
        summary.evaluation_success_count,
    )
    print(
        f"Done. total_records={summary.total_records}\n"
        f"subtitle_success_count={summary.subtitle_success_count}\n"
        f"evaluation_success_count={summary.evaluation_success_count}\n"
        f"csv={exported['csv']}\n"
        f"json={exported['json']}\n"
        f"md={exported['md']}\n"
        f"log={exported['log']}"
    )


if __name__ == "__main__":
    asyncio.run(async_main())
