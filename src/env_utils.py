from __future__ import annotations

PLACEHOLDER_PREFIXES = ("your_", "replace_", "填入", "请填写")


def normalize_env_value(value: str | None) -> str:
    """Normalize an environment value before placeholder checks."""
    if value is None:
        return ""
    return value.strip().strip('"').strip("'")


def is_real_env_value(value: str | None) -> bool:
    """Return True when an environment value is present and not a template placeholder."""
    stripped = normalize_env_value(value)
    if not stripped:
        return False
    lowered = stripped.lower()
    return not any(lowered.startswith(prefix.lower()) for prefix in PLACEHOLDER_PREFIXES)
