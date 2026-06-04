from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import cache_utils  # noqa: E402

DEFAULT_CACHE_DIR = ROOT / "results" / "cache"
SELF_CHECK_NAMESPACE = "_self_check"


@dataclass(frozen=True)
class CacheVerification:
    namespace: str
    key: str
    saved_path: Path
    miss_before_save: bool
    hit_after_save: bool
    miss_after_clear: bool


def verify_cache(*, cache_dir: Path | str = DEFAULT_CACHE_DIR) -> CacheVerification:
    """Verify cache miss, hit and clear behavior without touching business namespaces."""
    original_cache_dir = cache_utils.CACHE_DIR
    cache_utils.CACHE_DIR = Path(cache_dir)
    key = cache_utils.build_cache_key("cache-self-check", "v1")
    payload = {"status": "ok", "items": [1, 2, 3]}
    try:
        cache_utils.clear_cache(SELF_CHECK_NAMESPACE)
        miss_before_save = cache_utils.load_json_cache(SELF_CHECK_NAMESPACE, key) is None
        saved_path = cache_utils.save_json_cache(SELF_CHECK_NAMESPACE, key, payload)
        hit_after_save = cache_utils.load_json_cache(SELF_CHECK_NAMESPACE, key) == payload
        cache_utils.clear_cache(SELF_CHECK_NAMESPACE)
        miss_after_clear = cache_utils.load_json_cache(SELF_CHECK_NAMESPACE, key) is None
    finally:
        cache_utils.CACHE_DIR = original_cache_dir

    result = CacheVerification(
        namespace=SELF_CHECK_NAMESPACE,
        key=key,
        saved_path=saved_path,
        miss_before_save=miss_before_save,
        hit_after_save=hit_after_save,
        miss_after_clear=miss_after_clear,
    )
    if not (result.miss_before_save and result.hit_after_save and result.miss_after_clear):
        raise RuntimeError(f"Cache verification failed: {result}")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify cache miss/hit/clear behavior.")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR, help="Cache directory to verify")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = build_parser().parse_args()
    try:
        result = verify_cache(cache_dir=args.cache_dir)
    except (OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("Cache verification passed:")
    print(f"namespace={result.namespace}")
    print(f"miss_before_save={result.miss_before_save}")
    print(f"hit_after_save={result.hit_after_save}")
    print(f"miss_after_clear={result.miss_after_clear}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
