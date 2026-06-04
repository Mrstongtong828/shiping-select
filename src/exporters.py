from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.schema import SearchSummary, VideoRecord


def _inline_text(value: str) -> str:
    return " ".join(value.split())


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return ""
    return ",".join(f"{key}:{counts[key]}" for key in sorted(counts))


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
                "has_math": record.has_math,
                "has_code": record.has_code,
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


def _sort_records(records: list[VideoRecord]) -> list[VideoRecord]:
    return sorted(
        records,
        key=lambda item: (
            0 if item.recommend == "yes" else 1,
            -(item.relevance or -1),
            -(item.depth or -1),
            -(item.clarity or -1),
            -item.view,
        ),
    )


def _duration_label(seconds: int) -> str:
    if seconds <= 0:
        return "未知时长"
    minutes = seconds // 60
    if minutes < 1:
        return "1 分钟以内"
    return f"{minutes} 分钟"


def _record_line(record: VideoRecord) -> str:
    title = _inline_text(record.title) or "无标题"
    author = _inline_text(record.author) or "未知作者"
    reason = _inline_text(record.reason) or "暂未生成推荐理由。"
    parts = [
        f"[{title}]({record.url})",
        record.platform,
        author,
        f"相关性={record.relevance}" if record.relevance is not None else "相关性=待评估",
        f"深度={record.depth}" if record.depth is not None else "深度=待评估",
        f"清晰度={record.clarity}" if record.clarity is not None else "清晰度=待评估",
        f"适用对象={record.audience or '待评估'}",
        f"时长={_duration_label(record.duration)}",
    ]
    summary = " | ".join(parts)
    return f"- {summary} | {reason}"


def _bucket_name(record: VideoRecord) -> str:
    text = f"{record.title} {record.description}".lower()
    if record.has_code or any(
        token in text for token in ("python", "matlab", "sklearn", "numpy", "代码", "实操", "实战")
    ):
        return "代码实操层"
    if (
        any(token in text for token in ("应用", "案例", "实战应用", "人脸识别", "光谱", "降维"))
        and (record.depth or 0) >= 5
    ):
        return "应用案例层"
    if record.audience == "科普" or ((record.depth or 0) <= 4 and not record.has_math):
        return "入门理解层"
    if record.has_math or record.audience in {"本科进阶", "研究生"} or (record.depth or 0) >= 7:
        return "数学推导层"
    return "入门理解层"


def _build_sections(records: list[VideoRecord]) -> dict[str, list[VideoRecord]]:
    sections = {
        "入门理解层": [],
        "数学推导层": [],
        "代码实操层": [],
        "应用案例层": [],
    }
    for record in _sort_records(records):
        sections[_bucket_name(record)].append(record)
    return sections


def export_markdown(path: Path, topic: str, records: list[VideoRecord], summary: SearchSummary) -> None:
    preferred = [record for record in records if record.recommend == "yes"]
    display_records = preferred or _sort_records(records)
    sections = _build_sections(display_records)

    lines = [
        f"# {topic} 学习资源推荐",
        "",
        "## 运行摘要",
        f"- 候选总数：{summary.total_records}",
        f"- 字幕成功数：{summary.subtitle_success_count}",
        f"- 字幕成功率：{summary.subtitle_success_ratio:.0%}",
        f"- 评估成功数：{summary.evaluation_success_count}",
        f"- 评估成功率：{summary.evaluation_success_ratio:.0%}",
    ]
    platform_distribution = _format_counts(summary.platform_counts)
    subtitle_source_distribution = _format_counts(summary.subtitle_source_counts)
    if platform_distribution:
        lines.append(f"- 平台分布：{platform_distribution}")
    if subtitle_source_distribution:
        lines.append(f"- 字幕来源分布：{subtitle_source_distribution}")
    if summary.errors:
        lines.append(f"- 异常信息：{'；'.join(summary.errors[:5])}")

    lines.extend(
        [
            "",
            "## 推荐学习路径",
            "- 先看“入门理解层”，建立对主题的直观认识。",
            "- 再看“数学推导层”，补齐原理、公式与理论细节。",
            "- 然后看“代码实操层”，完成方法复现。",
            "- 最后看“应用案例层”，理解该主题在真实任务中的价值。",
        ]
    )

    for section_name in ("入门理解层", "数学推导层", "代码实操层", "应用案例层"):
        bucket = sections[section_name]
        lines.extend(["", f"## {section_name}"])
        if not bucket:
            lines.append("- 当前没有合适的视频。")
            continue
        for record in bucket[:5]:
            lines.append(_record_line(record))

    lines.extend(["", "## 候选总表（前 10 条）"])
    if not records:
        lines.append("- 当前没有可展示结果。")
    else:
        for record in _sort_records(records)[:10]:
            lines.append(_record_line(record))

    path.write_text("\n".join(lines), encoding="utf-8")


def export_run_log(path: Path, topic: str, summary: SearchSummary) -> None:
    lines = [
        f"topic={topic}",
        f"total_records={summary.total_records}",
        f"subtitle_success_count={summary.subtitle_success_count}",
        f"subtitle_success_ratio={summary.subtitle_success_ratio:.4f}",
        f"evaluation_success_count={summary.evaluation_success_count}",
        f"evaluation_success_ratio={summary.evaluation_success_ratio:.4f}",
        f"platform_counts={_format_counts(summary.platform_counts)}",
        f"subtitle_source_counts={_format_counts(summary.subtitle_source_counts)}",
        f"errors={len(summary.errors)}",
    ]
    lines.extend(f"error={error}" for error in summary.errors)
    path.write_text("\n".join(lines), encoding="utf-8")
