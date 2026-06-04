from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CSV_FIELDS = (
    "platform",
    "title",
    "url",
    "author",
    "view",
    "like",
    "has_subtitle",
    "relevance",
    "depth",
    "clarity",
    "audience",
    "recommend",
    "reason",
)
REQUIRED_MARKDOWN_FRAGMENTS = (
    "运行摘要",
    "推荐学习路径",
    "入门理解层",
    "数学推导层",
    "代码实操层",
    "应用案例层",
)


def _slugify_topic(topic: str) -> str:
    chars: list[str] = []
    for ch in topic:
        if ch.isalnum() or ch in {"_", "-", " "}:
            chars.append(ch)
        else:
            chars.append("_")
    return "".join(chars).strip().replace(" ", "_") or "results"


def _parse_run_log(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _read_int(values: dict[str, str], key: str) -> int:
    try:
        return int(values.get(key, "0") or 0)
    except ValueError as exc:
        raise ValueError(f"{key} is not an integer: {values.get(key)!r}") from exc


def _validate_final_run(
    *,
    log_path: Path,
    min_records: int,
    min_evaluation_ratio: float,
) -> int:
    values = _parse_run_log(log_path)
    total_records = _read_int(values, "total_records")
    evaluation_success_count = _read_int(values, "evaluation_success_count")
    required_evaluations = math.ceil(total_records * min_evaluation_ratio)

    if total_records < min_records:
        raise ValueError(f"total_records={total_records} is below required minimum {min_records}")
    if evaluation_success_count < required_evaluations:
        raise ValueError(
            "evaluation_success_count=" f"{evaluation_success_count} is below required minimum {required_evaluations}"
        )
    return total_records


def _validate_csv(csv_path: Path, required_platforms: tuple[str, ...], min_records: int) -> None:
    with csv_path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    fieldnames = rows[0].keys() if rows else []
    missing_fields = [field for field in REQUIRED_CSV_FIELDS if field not in fieldnames]
    if missing_fields:
        raise ValueError(f"CSV missing required field(s): {', '.join(missing_fields)}")
    if len(rows) < min_records:
        raise ValueError(f"CSV row count {len(rows)} is below required minimum {min_records}")

    platforms = {str(row.get("platform", "")).strip().lower() for row in rows}
    missing_platforms = [platform for platform in required_platforms if platform not in platforms]
    if missing_platforms:
        raise ValueError(f"CSV missing required platform(s): {', '.join(missing_platforms)}")


def _validate_json(json_path: Path, min_records: int) -> None:
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON is not valid: {exc}") from exc
    if not isinstance(payload, list):
        raise ValueError("JSON must be a list of video records")
    if len(payload) < min_records:
        raise ValueError(f"JSON record count {len(payload)} is below required minimum {min_records}")


def _validate_markdown(markdown_path: Path) -> None:
    text = markdown_path.read_text(encoding="utf-8")
    missing = [fragment for fragment in REQUIRED_MARKDOWN_FRAGMENTS if fragment not in text]
    if missing:
        raise ValueError(f"Markdown missing required section(s): {', '.join(missing)}")


def refresh_submission_samples(
    *,
    topic: str = "PCA 主成分分析",
    results_dir: Path | str = ROOT / "results",
    samples_dir: Path | str = ROOT / "输出样例",
    target_stem: str = "pca_主成分分析",
    min_records: int = 30,
    min_evaluation_ratio: float = 0.9,
    required_platforms: tuple[str, ...] = ("bilibili", "youtube"),
) -> list[Path]:
    """Copy a verified final run from results/ into the submission samples directory."""
    results_path = Path(results_dir)
    samples_path = Path(samples_dir)
    source_stem = _slugify_topic(topic)

    sources = {
        f"{target_stem}.csv": results_path / f"{source_stem}.csv",
        f"{target_stem}.json": results_path / f"{source_stem}.json",
        f"{target_stem}.md": results_path / f"{source_stem}.md",
        "eval_log.txt": results_path / f"{source_stem}_run.log",
    }
    missing = [str(path) for path in sources.values() if not path.exists() or path.stat().st_size <= 0]
    if missing:
        raise FileNotFoundError(f"Missing or empty final run artifact(s): {', '.join(missing)}")

    expected_records = _validate_final_run(
        log_path=sources["eval_log.txt"],
        min_records=min_records,
        min_evaluation_ratio=min_evaluation_ratio,
    )
    _validate_csv(sources[f"{target_stem}.csv"], required_platforms, expected_records)
    _validate_json(sources[f"{target_stem}.json"], expected_records)
    _validate_markdown(sources[f"{target_stem}.md"])

    samples_path.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for target_name, source_path in sources.items():
        target_path = samples_path / target_name
        shutil.copy2(source_path, target_path)
        copied.append(target_path)
    return copied


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refresh final submission samples from a verified results run.")
    parser.add_argument("--topic", default="PCA 主成分分析", help="Topic used for the final run")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results", help="Directory containing final results")
    parser.add_argument("--samples-dir", type=Path, default=ROOT / "输出样例", help="Directory to update")
    parser.add_argument("--target-stem", default="pca_主成分分析", help="Output sample filename stem")
    parser.add_argument("--min-records", type=int, default=30, help="Minimum total_records required in run log")
    parser.add_argument(
        "--required-platform",
        action="append",
        default=["bilibili", "youtube"],
        help="Platform that must appear in the final CSV; repeat to require multiple platforms",
    )
    parser.add_argument(
        "--min-evaluation-ratio",
        type=float,
        default=0.9,
        help="Minimum evaluation success ratio required before copying",
    )
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = build_parser().parse_args()
    try:
        copied = refresh_submission_samples(
            topic=args.topic,
            results_dir=args.results_dir,
            samples_dir=args.samples_dir,
            target_stem=args.target_stem,
            min_records=args.min_records,
            min_evaluation_ratio=args.min_evaluation_ratio,
            required_platforms=tuple(platform.lower() for platform in args.required_platform),
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("Refreshed submission samples:")
    for path in copied:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
