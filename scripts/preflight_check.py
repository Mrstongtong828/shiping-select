from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.env_utils import is_real_env_value  # noqa: E402


@dataclass(frozen=True)
class PreflightItem:
    name: str
    status: str
    detail: str


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _merged_env(env_file: Path, environ: Mapping[str, str]) -> dict[str, str]:
    values = _parse_env_file(env_file)
    for key, value in environ.items():
        if value:
            values[key] = value
    return values


def _is_real_value(value: str) -> bool:
    return is_real_env_value(value)


def _key_item(values: Mapping[str, str], name: str) -> PreflightItem:
    value = values.get(name, "")
    if not _is_real_value(value):
        return PreflightItem(name, "fail", "缺失或仍为占位符")
    return PreflightItem(name, "pass", f"已设置，length={len(value)}")


def _youtube_key_item(values: Mapping[str, str]) -> PreflightItem:
    value = values.get("YOUTUBE_API_KEY", "")
    if not _is_real_value(value):
        return PreflightItem(
            "YOUTUBE_API_KEY",
            "warn",
            "未设置真实 Key，将尝试 yt-dlp 搜索降级；如 YouTube 网络不可达，请配置代理或补充官方 Key",
        )
    return PreflightItem("YOUTUBE_API_KEY", "pass", f"已设置，length={len(value)}")


def _optional_item(values: Mapping[str, str], name: str, default: str) -> PreflightItem:
    value = values.get(name, "")
    if not _is_real_value(value):
        return PreflightItem(name, "warn", f"未设置，将使用默认值 {default}")
    return PreflightItem(name, "pass", f"已设置，length={len(value)}")


def run_preflight(
    *,
    env_file: Path | str = ROOT / ".env",
    project_root: Path | str = ROOT,
    environ: Mapping[str, str] | None = None,
) -> list[PreflightItem]:
    """Check whether local configuration is ready for the final online run."""
    env_path = Path(env_file)
    root = Path(project_root)
    env_values = _merged_env(env_path, environ or os.environ)

    results = [
        PreflightItem(
            ".env 文件", "pass" if env_path.exists() else "fail", str(env_path) if env_path.exists() else "文件不存在"
        ),
        _youtube_key_item(env_values),
        _key_item(env_values, "OPENAI_API_KEY"),
        _optional_item(env_values, "OPENAI_BASE_URL", "https://api.deepseek.com"),
        _optional_item(env_values, "OPENAI_MODEL", "deepseek-chat"),
        _optional_item(env_values, "ASR_MODEL", "small"),
        _optional_item(env_values, "ASR_COMPUTE_TYPE", "int8"),
        _optional_item(env_values, "ASR_DEVICE", "cpu"),
    ]

    proxy_keys = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")
    configured_proxy = [key for key in proxy_keys if _is_real_value(env_values.get(key, ""))]
    if configured_proxy:
        results.append(PreflightItem("代理配置", "pass", "已设置: " + ", ".join(configured_proxy)))
    else:
        results.append(PreflightItem("代理配置", "warn", "未设置代理；如 YouTube/OpenAI 无法访问，请配置代理"))

    douyin_path_text = env_values.get("DOUYIN_SAMPLE_JSON", "douyinpachong-main/foshan_hot_videos.json")
    douyin_path = Path(douyin_path_text)
    if not douyin_path.is_absolute():
        douyin_path = root / douyin_path
    if douyin_path.exists() and douyin_path.stat().st_size > 0:
        results.append(PreflightItem("抖音参考 JSON", "pass", str(douyin_path)))
    else:
        results.append(PreflightItem("抖音参考 JSON", "warn", f"文件不存在或为空: {douyin_path}"))

    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check local environment readiness for the final online run.")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env", help="Path to local .env")
    parser.add_argument("--project-root", type=Path, default=ROOT, help="Project root used to resolve relative paths")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    return parser


def _print_results(results: list[PreflightItem]) -> None:
    for item in results:
        print(f"[{item.status.upper()}] {item.name}: {item.detail}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    results = run_preflight(env_file=args.env_file, project_root=args.project_root)
    _print_results(results)
    failure_statuses = {"fail", "warn"} if args.strict else {"fail"}
    return 1 if any(item.status in failure_statuses for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
