import subprocess
import sys
from pathlib import Path

from scripts.verify_cache import verify_cache

ROOT = Path(__file__).resolve().parents[1]


def test_verify_cache_checks_miss_hit_and_clear(tmp_path):
    result = verify_cache(cache_dir=tmp_path / "cache")

    assert result.miss_before_save is True
    assert result.hit_after_save is True
    assert result.miss_after_clear is True
    assert result.namespace == "_self_check"


def test_verify_cache_cli_help_runs():
    result = subprocess.run(
        [sys.executable, "scripts/verify_cache.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Verify cache miss/hit/clear behavior" in result.stdout
