from __future__ import annotations

from pathlib import Path


PROMPT_PATH = Path("prompts/eval_template.txt")


def load_eval_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")

