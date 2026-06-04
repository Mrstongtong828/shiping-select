from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.acceptance_check import CheckResult, run_acceptance_checks

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "文档" / "终验审计报告.md"
STATUS_ORDER = ("pass", "warn", "fail")


def _format_detail(detail: str) -> str:
    return detail.replace("|", "\\|").replace("\n", "<br>")


def _build_result_table(results: list[CheckResult]) -> list[str]:
    if not results:
        return ["暂无记录。"]

    lines = ["| 状态 | 检查项 | 说明 |", "| --- | --- | --- |"]
    for item in results:
        lines.append(f"| {item.status} | {item.name} | {_format_detail(item.detail)} |")
    return lines


def generate_final_audit_markdown(results: list[CheckResult], *, generated_at: str | None = None) -> str:
    """Render acceptance-check results into a teacher-facing final audit report."""
    generated_time = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    counts = Counter(item.status for item in results)
    passed = [item for item in results if item.status == "pass"]
    pending = [item for item in results if item.status != "pass"]
    conclusion = (
        "当前仍存在失败项，需要先修复后再提交。"
        if counts["fail"]
        else (
            "当前离线自检无失败项；剩余 WARN 为完整外部平台复跑或最终提交样例刷新依赖，不能替代正式终验。"
            if counts["warn"]
            else "当前全部检查通过，可作为终验提交前的状态快照。"
        )
    )

    lines = [
        "# 终验审计报告",
        "",
        f"生成时间：{generated_time}",
        "",
        "本报告由 `python scripts\\final_audit.py` 基于 `scripts/acceptance_check.py` 的离线自检结果自动生成，"
        "用于集中说明项目当前通过项、待补齐项和终验风险。",
        "",
        "## 状态汇总",
        "",
        "| status | count |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {status} | {counts[status]} |" for status in STATUS_ORDER)
    lines.extend(
        [
            f"| total | {len(results)} |",
            "",
            "## 通过项",
            "",
            *_build_result_table(passed),
            "",
            "## 待补齐项",
            "",
            *_build_result_table(pending),
            "",
            "## 结论",
            "",
            conclusion,
            "",
        ]
    )
    return "\n".join(lines)


def write_final_audit_report(
    *,
    output_path: Path | str = DEFAULT_OUTPUT,
    results: list[CheckResult] | None = None,
    generated_at: str | None = None,
    strict: bool = False,
) -> Path:
    """Write the consolidated final audit report and return its path."""
    target_path = Path(output_path)
    if not target_path.is_absolute():
        target_path = ROOT / target_path
    target_path.parent.mkdir(parents=True, exist_ok=True)

    checked_results = results if results is not None else run_acceptance_checks(strict=strict)
    markdown = generate_final_audit_markdown(checked_results, generated_at=generated_at)
    target_path.write_text(markdown, encoding="utf-8")
    return target_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a consolidated final audit report.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Target Markdown report path")
    parser.add_argument("--strict", action="store_true", help="Treat acceptance warnings as failures")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = build_parser().parse_args()
    results = run_acceptance_checks(strict=args.strict)
    report_path = write_final_audit_report(output_path=args.output, results=results)
    print(f"Generated final audit report: {report_path}")
    return 1 if any(item.status == "fail" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
