from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import URLError
from urllib.request import urlopen as default_urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APP = ROOT / "app.py"


@dataclass(frozen=True)
class StreamlitVerification:
    ok: bool
    url: str
    status_code: int | None
    command: list[str]


def build_streamlit_command(*, python_executable: str, app_path: Path, port: int) -> list[str]:
    return [
        python_executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.headless",
        "true",
        "--server.port",
        str(port),
        "--browser.gatherUsageStats",
        "false",
    ]


def verify_streamlit_ui(
    *,
    app_path: Path | str = DEFAULT_APP,
    port: int = 8501,
    timeout_seconds: float = 20,
    poll_interval_seconds: float = 0.5,
    popen_factory: Callable[..., subprocess.Popen] = subprocess.Popen,
    urlopen: Callable[..., object] = default_urlopen,
) -> StreamlitVerification:
    """Start Streamlit headlessly and verify the app root returns HTTP 200."""
    app = Path(app_path)
    command = build_streamlit_command(python_executable=sys.executable, app_path=app, port=port)
    url = f"http://127.0.0.1:{port}/"
    process = popen_factory(
        command,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    status_code: int | None = None
    try:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() <= deadline:
            if process.poll() is not None:
                break
            try:
                with urlopen(url, timeout=2) as response:
                    status_code = getattr(response, "status", None) or getattr(response, "code", None)
                    if status_code == 200:
                        return StreamlitVerification(True, url, status_code, command)
            except (OSError, URLError):
                pass
            time.sleep(poll_interval_seconds)
        return StreamlitVerification(False, url, status_code, command)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify Streamlit UI starts and returns HTTP 200.")
    parser.add_argument("--app", type=Path, default=DEFAULT_APP, help="Streamlit app path")
    parser.add_argument("--port", type=int, default=8501, help="Local port to use")
    parser.add_argument("--timeout", type=float, default=20, help="Seconds to wait for HTTP 200")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = build_parser().parse_args()
    result = verify_streamlit_ui(app_path=args.app, port=args.port, timeout_seconds=args.timeout)
    if not result.ok:
        print(f"ERROR: Streamlit UI did not return HTTP 200 at {result.url}", file=sys.stderr)
        return 1
    print("Streamlit UI verification passed:")
    print(f"url={result.url}")
    print(f"status_code={result.status_code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
