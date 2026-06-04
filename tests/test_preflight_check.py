import subprocess
import sys
from pathlib import Path

from scripts.preflight_check import run_preflight

ROOT = Path(__file__).resolve().parents[1]


def test_preflight_fails_when_env_file_missing(tmp_path):
    results = run_preflight(env_file=tmp_path / ".env", project_root=tmp_path, environ={})

    statuses = {item.name: item.status for item in results}
    assert statuses[".env 文件"] == "fail"
    assert statuses["YOUTUBE_API_KEY"] == "warn"
    assert statuses["OPENAI_API_KEY"] == "fail"


def test_preflight_rejects_placeholder_keys_without_leaking_values(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "YOUTUBE_API_KEY=your_youtube_api_key",
                "OPENAI_API_KEY=sk-real-looking-but-should-not-print",
                "OPENAI_BASE_URL=https://api.deepseek.com",
                "OPENAI_MODEL=deepseek-chat",
            ]
        ),
        encoding="utf-8",
    )

    results = run_preflight(env_file=env_file, project_root=tmp_path, environ={})

    by_name = {item.name: item for item in results}
    assert by_name["YOUTUBE_API_KEY"].status == "warn"
    assert by_name["OPENAI_API_KEY"].status == "pass"
    combined_details = "\n".join(item.detail for item in results)
    assert "sk-real-looking-but-should-not-print" not in combined_details
    assert "length=" in by_name["OPENAI_API_KEY"].detail


def test_preflight_passes_with_required_keys_and_existing_douyin_json(tmp_path):
    env_file = tmp_path / ".env"
    sample_json = tmp_path / "douyin.json"
    sample_json.write_text('{"videos": []}', encoding="utf-8")
    env_file.write_text(
        "\n".join(
            [
                "YOUTUBE_API_KEY=AIzaSy_fake_key_for_test",
                "OPENAI_API_KEY=sk-fake-key-for-test",
                "OPENAI_BASE_URL=https://api.deepseek.com",
                "OPENAI_MODEL=deepseek-chat",
                f"DOUYIN_SAMPLE_JSON={sample_json}",
            ]
        ),
        encoding="utf-8",
    )

    results = run_preflight(env_file=env_file, project_root=tmp_path, environ={"HTTP_PROXY": "http://127.0.0.1:7890"})

    by_name = {item.name: item for item in results}
    assert by_name[".env 文件"].status == "pass"
    assert by_name["YOUTUBE_API_KEY"].status == "pass"
    assert by_name["OPENAI_API_KEY"].status == "pass"
    assert by_name["代理配置"].status == "pass"
    assert by_name["抖音参考 JSON"].status == "pass"


def test_preflight_cli_reports_missing_env_cleanly(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/preflight_check.py",
            "--env-file",
            str(tmp_path / ".env"),
            "--project-root",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "[FAIL] .env 文件" in result.stdout
    assert "Traceback" not in result.stderr
