import subprocess
import sys
from pathlib import Path

from scripts.run_final_acceptance import build_final_acceptance_steps, build_step_commands

ROOT = Path(__file__).resolve().parents[1]


def test_build_step_commands_include_final_acceptance_flow():
    commands = build_step_commands(
        python_executable="python",
        topic="PCA 主成分分析",
        max_results=30,
        enable_asr=True,
    )

    command_text = [" ".join(command) for command in commands]

    assert command_text[0] == "python scripts/preflight_check.py"
    assert any(
        "main.py" in command and "--platform" in command and "bilibili,youtube" in command for command in command_text
    )
    assert any("scripts/refresh_submission_samples.py" in command for command in command_text)
    assert any("scripts/acceptance_check.py --strict" in command for command in command_text)
    assert any("scripts/final_audit.py --strict" in command for command in command_text)
    assert any("scripts/generate_demo_recording.py" in command for command in command_text)
    assert any("scripts/package_submission.py" in command for command in command_text)


def test_build_final_acceptance_steps_has_human_readable_names():
    steps = build_final_acceptance_steps(
        python_executable="python",
        topic="PCA 主成分分析",
        max_results=30,
        enable_asr=False,
    )

    assert steps[0].name == "终验前置检查"
    assert steps[-1].name == "生成提交包"
    assert all(step.command for step in steps)
    assert "--enable-asr" not in " ".join(" ".join(step.command) for step in steps)


def test_run_final_acceptance_cli_dry_run_prints_steps():
    result = subprocess.run(
        [sys.executable, "scripts/run_final_acceptance.py", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0
    assert "Run final online acceptance workflow" in result.stdout
    assert "[DRY-RUN]" in result.stdout
    assert "scripts/preflight_check.py" in result.stdout
