from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOPIC = "PCA 主成分分析"
DEFAULT_MAX_RESULTS = 30


@dataclass(frozen=True)
class AcceptanceStep:
    name: str
    command: list[str]


def build_final_acceptance_steps(
    *,
    python_executable: str,
    topic: str,
    max_results: int,
    enable_asr: bool,
) -> list[AcceptanceStep]:
    """Build the ordered command plan for the final online acceptance run."""
    main_command = [
        python_executable,
        "main.py",
        "--topic",
        topic,
        "--platform",
        "bilibili,youtube",
        "--max",
        str(max_results),
    ]
    if enable_asr:
        main_command.append("--enable-asr")

    return [
        AcceptanceStep("终验前置检查", [python_executable, "scripts/preflight_check.py"]),
        AcceptanceStep("真实双平台完整运行", main_command),
        AcceptanceStep("刷新提交样例", [python_executable, "scripts/refresh_submission_samples.py", "--topic", topic]),
        AcceptanceStep("严格离线自检", [python_executable, "scripts/acceptance_check.py", "--strict"]),
        AcceptanceStep("刷新终验审计报告", [python_executable, "scripts/final_audit.py", "--strict"]),
        AcceptanceStep("生成演示录屏", [python_executable, "scripts/generate_demo_recording.py"]),
        AcceptanceStep("生成提交包", [python_executable, "scripts/package_submission.py"]),
    ]


def build_step_commands(
    *,
    python_executable: str,
    topic: str,
    max_results: int,
    enable_asr: bool,
) -> list[list[str]]:
    """Return only command argv lists for tests and machine-readable previews."""
    return [
        step.command
        for step in build_final_acceptance_steps(
            python_executable=python_executable,
            topic=topic,
            max_results=max_results,
            enable_asr=enable_asr,
        )
    ]


def _format_command(command: list[str]) -> str:
    return " ".join(command)


def run_final_acceptance(steps: list[AcceptanceStep], *, dry_run: bool = False) -> int:
    """Run or preview final acceptance commands in order, stopping at the first failure."""
    print("Run final online acceptance workflow")
    for index, step in enumerate(steps, start=1):
        prefix = "[DRY-RUN]" if dry_run else "[RUN]"
        print(f"{prefix} {index}. {step.name}: {_format_command(step.command)}")
        if dry_run:
            continue
        completed = subprocess.run(step.command, cwd=ROOT, check=False)
        if completed.returncode != 0:
            print(f"[FAIL] {step.name}: exit_code={completed.returncode}", file=sys.stderr)
            return completed.returncode
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run final online acceptance workflow.")
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help="Final run topic")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX_RESULTS, help="Maximum candidate videos")
    parser.add_argument("--enable-asr", action="store_true", help="Enable ASR fallback in the final online run")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them")
    parser.add_argument("--python", default=sys.executable, help="Python executable used for child commands")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = build_parser().parse_args()
    steps = build_final_acceptance_steps(
        python_executable=args.python,
        topic=args.topic,
        max_results=args.max,
        enable_asr=args.enable_asr,
    )
    return run_final_acceptance(steps, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
