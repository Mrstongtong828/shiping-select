from __future__ import annotations

import argparse
import importlib
import os
import sys
from dataclasses import dataclass
from typing import Callable

DEFAULT_ASR_MODEL = "small"
DEFAULT_ASR_COMPUTE_TYPE = "int8"
DEFAULT_ASR_DEVICE = "cpu"


@dataclass(frozen=True)
class AsrEnvironmentVerification:
    yt_dlp_available: bool
    faster_whisper_available: bool
    asr_model: str
    asr_compute_type: str
    asr_device: str


def _import_available(name: str, import_module: Callable[[str], object]) -> bool:
    try:
        import_module(name)
    except ImportError:
        return False
    return True


def verify_asr_environment(
    *,
    import_module: Callable[[str], object] = importlib.import_module,
) -> AsrEnvironmentVerification:
    """Verify ASR fallback dependencies and effective environment defaults without downloading models."""
    result = AsrEnvironmentVerification(
        yt_dlp_available=_import_available("yt_dlp", import_module),
        faster_whisper_available=_import_available("faster_whisper", import_module),
        asr_model=os.getenv("ASR_MODEL", DEFAULT_ASR_MODEL),
        asr_compute_type=os.getenv("ASR_COMPUTE_TYPE", DEFAULT_ASR_COMPUTE_TYPE),
        asr_device=os.getenv("ASR_DEVICE", DEFAULT_ASR_DEVICE),
    )
    if not (result.yt_dlp_available and result.faster_whisper_available):
        raise RuntimeError(f"ASR dependency check failed: {result}")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify ASR fallback environment without downloading models.")
    parser.add_argument("--allow-missing", action="store_true", help="Report missing dependencies without failing")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = build_parser().parse_args()
    try:
        result = verify_asr_environment()
    except RuntimeError as exc:
        if not args.allow_missing:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        result_text = str(exc)
        print(f"ASR environment warning: {result_text}")
        return 0

    print("ASR environment verification passed:")
    print(f"yt_dlp_available={result.yt_dlp_available}")
    print(f"faster_whisper_available={result.faster_whisper_available}")
    print(f"ASR_MODEL={result.asr_model}")
    print(f"ASR_COMPUTE_TYPE={result.asr_compute_type}")
    print(f"ASR_DEVICE={result.asr_device}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
