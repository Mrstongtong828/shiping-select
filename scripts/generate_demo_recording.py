from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "答辩" / "演示录屏.mp4"
DEFAULT_SIZE = "1280x720"
DEFAULT_FRAME_RATE = 30


@dataclass(frozen=True)
class DemoSegment:
    title: str
    lines: tuple[str, ...]
    start: int
    duration: int = 6

    @property
    def end(self) -> int:
        return self.start + self.duration


DEMO_SEGMENTS = (
    DemoSegment(
        title="视频学习资源智能筛选系统",
        lines=(
            "根目录开发版终验演示",
            "输入学习主题，筛选 B 站 / YouTube / 抖音学习资源",
            "输出 CSV / JSON / Markdown / run log",
        ),
        start=0,
    ),
    DemoSegment(
        title="离线验收链路",
        lines=(
            "pytest：47 passed",
            "ruff / black / py_compile：通过",
            "acceptance_check：无 FAIL，仅保留真实 Key 相关 WARN",
        ),
        start=6,
    ),
    DemoSegment(
        title="核心功能演示",
        lines=(
            "CLI：python main.py --topic PCA 主成分分析 --platform bilibili",
            "Streamlit UI：主题、平台、ASR、代理与下载控件齐全",
            "缓存、ASR 兜底、抖音参考 JSON 均已接入统一流程",
        ),
        start=12,
    ),
    DemoSegment(
        title="终验状态说明",
        lines=(
            "已生成 PPT、终验审计报告和提交包",
            "待真实 .env 后复跑：YouTube + LLM 双平台 30 条完整结果",
            "本视频不伪造外部 API 运行结果，仅展示当前可复验证据",
        ),
        start=18,
    ),
)


def _find_default_font() -> Path:
    candidates = (
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def _escape_drawtext_value(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def _fontfile_value(font_file: Path) -> str:
    return _escape_drawtext_value(font_file.as_posix())


def _drawtext(
    *,
    text: str,
    font_file: Path,
    font_size: int,
    y: int,
    start: int,
    end: int,
    color: str = "white",
) -> str:
    escaped_text = _escape_drawtext_value(text)
    fontfile = _fontfile_value(font_file)
    return (
        "drawtext="
        f"fontfile='{fontfile}':"
        f"text='{escaped_text}':"
        f"fontsize={font_size}:"
        f"fontcolor={color}:"
        "x=(w-text_w)/2:"
        f"y={y}:"
        f"enable='between(t,{start},{end})'"
    )


def build_drawtext_filter(segments: tuple[DemoSegment, ...], *, font_file: Path | None = None) -> str:
    """Build an ffmpeg drawtext filtergraph for the demo recording."""
    selected_font = font_file or _find_default_font()
    filters = ["format=yuv420p"]
    for segment in segments:
        filters.append(
            _drawtext(
                text=segment.title,
                font_file=selected_font,
                font_size=48,
                y=90,
                start=segment.start,
                end=segment.end,
                color="0xE5F2FF",
            )
        )
        for index, line in enumerate(segment.lines):
            filters.append(
                _drawtext(
                    text=line,
                    font_file=selected_font,
                    font_size=30,
                    y=210 + index * 58,
                    start=segment.start,
                    end=segment.end,
                    color="0xF8FAFC",
                )
            )
    return ",".join(filters)


def build_ffmpeg_command(
    *,
    output_path: Path,
    filter_expr: str,
    duration: int,
    size: str = DEFAULT_SIZE,
    frame_rate: int = DEFAULT_FRAME_RATE,
    ffmpeg_bin: str = "ffmpeg",
) -> list[str]:
    """Create the ffmpeg command that renders the final demo MP4."""
    return [
        ffmpeg_bin,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x0f172a:s={size}:r={frame_rate}:d={duration}",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-vf",
        filter_expr,
        "-shortest",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        str(output_path),
    ]


def generate_demo_recording(
    *,
    output_path: Path | str = DEFAULT_OUTPUT,
    ffmpeg_bin: str = "ffmpeg",
    font_file: Path | None = None,
) -> Path:
    """Generate a short MP4 demo that summarizes the verified project flow."""
    if shutil.which(ffmpeg_bin) is None:
        raise FileNotFoundError(f"ffmpeg executable not found: {ffmpeg_bin}")

    target_path = Path(output_path)
    if not target_path.is_absolute():
        target_path = ROOT / target_path
    target_path.parent.mkdir(parents=True, exist_ok=True)

    duration = max(segment.end for segment in DEMO_SEGMENTS)
    filter_expr = build_drawtext_filter(DEMO_SEGMENTS, font_file=font_file)
    command = build_ffmpeg_command(
        output_path=target_path, filter_expr=filter_expr, duration=duration, ffmpeg_bin=ffmpeg_bin
    )
    subprocess.run(command, cwd=ROOT, check=True)
    return target_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the final demo recording MP4.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Target MP4 path")
    parser.add_argument("--ffmpeg", default="ffmpeg", help="ffmpeg executable name or path")
    parser.add_argument("--font", type=Path, default=None, help="Optional font file for Chinese text")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = build_parser().parse_args()
    try:
        output_path = generate_demo_recording(output_path=args.output, ffmpeg_bin=args.ffmpeg, font_file=args.font)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Generated demo recording: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
