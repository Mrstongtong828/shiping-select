from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
from typing import Awaitable

from dotenv import load_dotenv

from src.evaluate import evaluate_records
from src.exporters import export_csv, export_json, export_markdown, export_run_log
from src.logging_utils import setup_logger
from src.schema import SearchSummary, VideoRecord
from src.search_bilibili import search_bilibili_videos
from src.search_youtube import search_youtube_videos


RESULTS_DIR = Path("results")
LOGGER = logging.getLogger("video_finder")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Video learning resource finder")
    parser.add_argument("--topic", required=True, help="Search topic, for example: PCA 主成分分析")
    parser.add_argument(
        "--platform",
        default="bilibili,youtube",
        help="Comma-separated platforms: bilibili,youtube",
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
    return parser


def slugify_topic(topic: str) -> str:
    chars: list[str] = []
    for ch in topic:
        if ch.isalnum() or ch in {"_", "-", " "} or ("一" <= ch <= "鿿"):
            chars.append(ch)
        else:
            chars.append("_")
    return "".join(chars).strip().replace(" ", "_") or "results"


async def gather_records(
    topic: str,
    platforms: list[str],
    max_results: int,
    subtitle_limit: int,
) -> tuple[list[VideoRecord], list[str]]:
    platform_list = [item.strip().lower() for item in platforms if item.strip()]
    if not platform_list:
        raise ValueError("At least one platform is required")

    per_platform = max(1, max_results // len(platform_list))
    coros: dict[str, Awaitable[list[VideoRecord]]] = {}

    if "bilibili" in platform_list:
        coros["bilibili"] = search_bilibili_videos(topic=topic, limit=per_platform, subtitle_limit=subtitle_limit)
    if "youtube" in platform_list:
        coros["youtube"] = search_youtube_videos(topic=topic, limit=per_platform, subtitle_limit=subtitle_limit)

    results = await asyncio.gather(*coros.values(), return_exceptions=True)
    merged: list[VideoRecord] = []
    errors: list[str] = []
    for platform_name, batch in zip(coros, results):
        if isinstance(batch, Exception):
            message = f"{platform_name} search failed: {batch}"
            LOGGER.error(message)
            errors.append(message)
            continue
        LOGGER.info("%s search finished with %s records", platform_name, len(batch))
        merged.extend(batch)

    return merged[:max_results], errors


def build_summary(records: list[VideoRecord], errors: list[str]) -> SearchSummary:
    total_records = len(records)
    subtitle_success_count = 0
    evaluation_success_count = 0
    for record in records:
        if record.has_subtitle:
            subtitle_success_count += 1
        if record.recommend in {"yes", "no"}:
            evaluation_success_count += 1
    return SearchSummary(
        total_records=total_records,
        subtitle_success_count=subtitle_success_count,
        subtitle_success_ratio=subtitle_success_count / total_records if total_records else 0.0,
        evaluation_success_count=evaluation_success_count,
        evaluation_success_ratio=evaluation_success_count / total_records if total_records else 0.0,
        errors=errors,
    )


def export_results(topic: str, records: list[VideoRecord], summary: SearchSummary) -> dict[str, Path]:
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

    platforms = [item.strip() for item in args.platform.split(",") if item.strip()]
    LOGGER.info("Start topic=%s platforms=%s max=%s", args.topic, ",".join(platforms), args.max)

    records, errors = await gather_records(
        topic=args.topic,
        platforms=platforms,
        max_results=args.max,
        subtitle_limit=args.subtitle_limit,
    )
    if not args.skip_evaluate:
        evaluated_records, evaluation_errors = await evaluate_records(args.topic, records)
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
