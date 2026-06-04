import subprocess
import sys
from pathlib import Path

from scripts.verify_asr import verify_asr_environment

ROOT = Path(__file__).resolve().parents[1]


def test_verify_asr_environment_reports_imports_and_defaults(monkeypatch):
    monkeypatch.delenv("ASR_MODEL", raising=False)
    monkeypatch.delenv("ASR_COMPUTE_TYPE", raising=False)
    monkeypatch.delenv("ASR_DEVICE", raising=False)

    result = verify_asr_environment(import_module=lambda name: object())

    assert result.yt_dlp_available is True
    assert result.faster_whisper_available is True
    assert result.asr_model == "small"
    assert result.asr_compute_type == "int8"
    assert result.asr_device == "cpu"


def test_verify_asr_environment_uses_env_overrides(monkeypatch):
    monkeypatch.setenv("ASR_MODEL", "tiny")
    monkeypatch.setenv("ASR_COMPUTE_TYPE", "float32")
    monkeypatch.setenv("ASR_DEVICE", "cuda")

    result = verify_asr_environment(import_module=lambda name: object())

    assert result.asr_model == "tiny"
    assert result.asr_compute_type == "float32"
    assert result.asr_device == "cuda"


def test_verify_asr_cli_help_runs():
    result = subprocess.run(
        [sys.executable, "scripts/verify_asr.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Verify ASR fallback environment" in result.stdout
