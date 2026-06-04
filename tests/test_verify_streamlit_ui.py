import subprocess
import sys
from pathlib import Path
from urllib.error import URLError

from scripts.verify_streamlit_ui import build_streamlit_command, verify_streamlit_ui

ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class FakeProcess:
    def __init__(self):
        self.terminated = False
        self.waited = False

    def poll(self):
        return None

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.waited = True


def test_build_streamlit_command_uses_headless_server_options():
    command = build_streamlit_command(
        python_executable="python",
        app_path=Path("app.py"),
        port=8510,
    )

    assert command[:4] == ["python", "-m", "streamlit", "run"]
    assert "app.py" in command
    assert "--server.headless" in command
    assert "true" in command
    assert "--server.port" in command
    assert "8510" in command


def test_verify_streamlit_ui_waits_for_http_200_and_stops_process(tmp_path):
    process = FakeProcess()
    calls = {"count": 0}

    def fake_popen(command, **kwargs):
        calls["command"] = command
        return process

    def fake_urlopen(url, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            raise URLError("not ready")
        return FakeResponse()

    result = verify_streamlit_ui(
        app_path=tmp_path / "app.py",
        port=8511,
        timeout_seconds=1,
        poll_interval_seconds=0,
        popen_factory=fake_popen,
        urlopen=fake_urlopen,
    )

    assert result.ok is True
    assert result.status_code == 200
    assert result.url == "http://127.0.0.1:8511/"
    assert calls["count"] == 2
    assert "streamlit" in calls["command"]
    assert process.terminated is True
    assert process.waited is True


def test_verify_streamlit_ui_cli_help_runs():
    result = subprocess.run(
        [sys.executable, "scripts/verify_streamlit_ui.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Verify Streamlit UI starts and returns HTTP 200" in result.stdout
