from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "提交包" / "视频学习资源智能筛选系统_终验提交包.zip"

INCLUDE_PATHS = (
    "README.md",
    "goal.md",
    ".env.example",
    "main.py",
    "app.py",
    "requirements.txt",
    "pyproject.toml",
    "prompts",
    "src",
    "scripts",
    "tests",
    "文档",
    "评估表",
    "答辩",
    "输出样例",
)
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    ".pytest_cache",
    "__pycache__",
    "results",
    "cache",
    "node_modules",
    "提交包",
}
EXCLUDE_FILE_NAMES = {".env"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".pyd", ".log"}


def _should_include(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if path.name in EXCLUDE_FILE_NAMES:
        return False
    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return False
    return not any(part in EXCLUDE_DIRS for part in relative.parts)


def _iter_submission_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for relative in INCLUDE_PATHS:
        path = root / relative
        if not path.exists():
            continue
        if path.is_file():
            if _should_include(path, root):
                files.append(path)
            continue
        for child in path.rglob("*"):
            if child.is_file() and _should_include(child, root):
                files.append(child)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def _missing_include_paths(root: Path) -> list[str]:
    return [relative for relative in INCLUDE_PATHS if not (root / relative).exists()]


def create_submission_package(*, root: Path | str = ROOT, output_path: Path | str = DEFAULT_OUTPUT) -> Path:
    """Create a zip package containing deliverables while excluding private/runtime files."""
    root_path = Path(root).resolve()
    target_path = Path(output_path)
    if not target_path.is_absolute():
        target_path = root_path / target_path
    target_path.parent.mkdir(parents=True, exist_ok=True)

    missing = _missing_include_paths(root_path)
    if missing:
        raise FileNotFoundError(f"Missing required submission path(s): {', '.join(missing)}")

    files = _iter_submission_files(root_path)
    if not files:
        raise FileNotFoundError(f"No submission files found under {root_path}")

    with zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root_path).as_posix())
    return target_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a submission package without private or runtime files.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Project root to package")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Target zip path")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = build_parser().parse_args()
    try:
        package_path = create_submission_package(root=args.root, output_path=args.output)
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Created submission package: {package_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
