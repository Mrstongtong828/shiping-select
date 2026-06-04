import subprocess
import sys
from pathlib import Path

from scripts.acceptance_check import CheckResult
from scripts.final_audit import generate_final_audit_markdown, write_final_audit_report

ROOT = Path(__file__).resolve().parents[1]


def test_generate_final_audit_markdown_summarizes_results():
    markdown = generate_final_audit_markdown(
        [
            CheckResult(name="A", status="pass", detail="ok"),
            CheckResult(name="B", status="warn", detail="needs work"),
            CheckResult(name="C", status="fail", detail="broken"),
        ],
        generated_at="2026-06-01 12:00:00",
    )

    assert "# 终验审计报告" in markdown
    assert "生成时间：2026-06-01 12:00:00" in markdown
    assert "| pass | 1 |" in markdown
    assert "| warn | 1 |" in markdown
    assert "| fail | 1 |" in markdown
    assert "## 通过项" in markdown
    assert "## 待补齐项" in markdown
    assert "A" in markdown
    assert "B" in markdown
    assert "C" in markdown


def test_write_final_audit_report_creates_file(tmp_path):
    output = tmp_path / "最终审计报告.md"

    path = write_final_audit_report(
        output_path=output,
        results=[
            CheckResult(name="A", status="pass", detail="ok"),
            CheckResult(name="B", status="warn", detail="needs work"),
        ],
        generated_at="2026-06-01 12:00:00",
    )

    assert path == output
    assert output.read_text(encoding="utf-8").startswith("# 终验审计报告")


def test_final_audit_cli_help_runs():
    result = subprocess.run(
        [sys.executable, "scripts/final_audit.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Generate a consolidated final audit report" in result.stdout
