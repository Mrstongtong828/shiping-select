import subprocess
import sys
from pathlib import Path

from scripts.generate_demo_recording import DEMO_SEGMENTS, build_drawtext_filter, build_ffmpeg_command

ROOT = Path(__file__).resolve().parents[1]


def test_build_drawtext_filter_contains_demo_sections():
    filter_expr = build_drawtext_filter(DEMO_SEGMENTS, font_file=Path("C:/Windows/Fonts/msyh.ttc"))

    assert "drawtext" in filter_expr
    assert "视频学习资源智能筛选系统" in filter_expr
    assert "acceptance_check" in filter_expr
    assert "Streamlit UI" in filter_expr
    assert "YouTube" in filter_expr
    assert "between(t,0,6)" in filter_expr


def test_build_ffmpeg_command_targets_mp4(tmp_path):
    output_path = tmp_path / "演示录屏.mp4"

    command = build_ffmpeg_command(output_path=output_path, filter_expr="drawtext=text='demo'", duration=3)

    assert command[0] == "ffmpeg"
    assert str(output_path) in command
    assert "libx264" in command
    assert "yuv420p" in command


def test_generate_demo_recording_cli_help_runs():
    result = subprocess.run(
        [sys.executable, "scripts/generate_demo_recording.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Generate the final demo recording MP4" in result.stdout
