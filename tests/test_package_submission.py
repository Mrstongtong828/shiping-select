import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from scripts.package_submission import create_submission_package

ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, text: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_create_submission_package_includes_required_materials_and_excludes_private_files(tmp_path):
    root = tmp_path / "project"
    output = tmp_path / "submission.zip"
    for relative in (
        "README.md",
        "goal.md",
        ".env.example",
        "main.py",
        "app.py",
        "requirements.txt",
        "pyproject.toml",
        "prompts/eval_template.txt",
        "src/schema.py",
        "scripts/acceptance_check.py",
        "tests/test_main.py",
        "文档/README.md",
        "评估表/人工对照评估结果.md",
        "答辩/答辩PPT.pptx",
        "输出样例/pca_主成分分析.csv",
    ):
        _write(root / relative)
    for relative in (
        ".env",
        ".venv/secret.txt",
        "results/cache/cache.json",
        "results/PCA_主成分分析.csv",
        "src/__pycache__/schema.pyc",
        ".pytest_cache/state",
    ):
        _write(root / relative)

    package_path = create_submission_package(root=root, output_path=output)

    assert package_path == output
    with zipfile.ZipFile(package_path) as archive:
        names = set(archive.namelist())

    assert "README.md" in names
    assert "文档/README.md" in names
    assert "评估表/人工对照评估结果.md" in names
    assert "答辩/答辩PPT.pptx" in names
    assert "输出样例/pca_主成分分析.csv" in names
    assert ".env" not in names
    assert ".venv/secret.txt" not in names
    assert "results/PCA_主成分分析.csv" not in names
    assert "results/cache/cache.json" not in names
    assert "src/__pycache__/schema.pyc" not in names
    assert ".pytest_cache/state" not in names


def test_package_submission_cli_help_runs():
    result = subprocess.run(
        [sys.executable, "scripts/package_submission.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Create a submission package" in result.stdout


def test_create_submission_package_fails_when_required_materials_missing(tmp_path):
    root = tmp_path / "project"
    output = tmp_path / "submission.zip"
    _write(root / "README.md")

    with pytest.raises(FileNotFoundError, match="Missing required submission path"):
        create_submission_package(root=root, output_path=output)

    assert not output.exists()
