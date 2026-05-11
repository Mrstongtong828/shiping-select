from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.schema import SearchSummary, VideoRecord


def build_csv_rows(records: list[VideoRecord]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record in records:
        rows.append(
            {
                "platform": record.platform,
                "title": record.title,
                "url": record.url,
                "author": record.author,
                "view": record.view,
                "like": record.like,
                "has_subtitle": record.has_subtitle,
                "relevance": record.relevance,
                "depth": record.depth,
                "clarity": record.clarity,
                "audience": record.audience,
                "recommend": record.recommend,
                "reason": record.reason,
                "video_id": record.video_id,
                "duration": record.duration,
                "publish_time": record.publish_time,
                "subtitle_language": record.subtitle_language,
                "subtitle_source": record.subtitle_source,
            }
        )
    return rows


def export_csv(path: Path, records: list[VideoRecord]) -> None:
    pd.DataFrame(build_csv_rows(records)).to_csv(path, index=False, encoding="utf-8-sig")


def export_json(path: Path, records: list[VideoRecord]) -> None:
    payload = [record.model_dump() for record in records]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def export_markdown(path: Path, topic: str, records: list[VideoRecord], summary: SearchSummary) -> None:
    recommended = [record for record in records if record.recommend == "yes"]
    fallback = recommended or records

    lines = [
        f"# {topic} Learning Resource Results",
        "",
        "## Summary",
        f"- Total records: {summary.total_records}",
        f"- Subtitle success count: {summary.subtitle_success_count}",
        f"- Subtitle success ratio: {summary.subtitle_success_ratio:.0%}",
    ]
    if summary.errors:
        lines.append(f"- Errors: {'; '.join(summary.errors)}")

    lines.extend(["", "## Candidate List"])
    if not fallback:
        lines.append("- No records available")
    else:
        for record in fallback[:10]:
            reason = record.reason or "Evaluation module not connected yet."
            lines.append(f"- [{record.title}]({record.url}) | {record.platform} | {reason}")

    path.write_text("\n".join(lines), encoding="utf-8")


def export_run_log(path: Path, topic: str, summary: SearchSummary) -> None:
    lines = [
        f"topic={topic}",
        f"total_records={summary.total_records}",
        f"subtitle_success_count={summary.subtitle_success_count}",
        f"subtitle_success_ratio={summary.subtitle_success_ratio:.4f}",
        f"errors={len(summary.errors)}",
    ]
    lines.extend(f"error={error}" for error in summary.errors)
    path.write_text("\n".join(lines), encoding="utf-8")
