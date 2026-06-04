from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path

from pydantic import ValidationError

from src.cache_utils import build_cache_key, load_json_cache, save_json_cache
from src.env_utils import is_real_env_value
from src.schema import EvaluationResult, VideoRecord

PROMPT_PATH = Path("prompts/eval_template.txt")
LOGGER = logging.getLogger("video_finder")


def load_eval_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def evaluation_enabled() -> bool:
    return is_real_env_value(os.getenv("OPENAI_API_KEY"))


def _clip_text(text: str, limit: int) -> str:
    return text[:limit].strip()


def _build_user_payload(topic: str, record: VideoRecord) -> str:
    payload = {
        "topic": topic,
        "platform": record.platform,
        "title": record.title,
        "author": record.author,
        "description": _clip_text(record.description, 1200),
        "subtitle_text": _clip_text(record.subtitle_text, 5000),
        "view": record.view,
        "like": record.like,
        "duration_seconds": record.duration,
        "publish_time": record.publish_time,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _create_client():
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise RuntimeError("Missing openai dependency. Please install requirements.txt") from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not is_real_env_value(api_key):
        raise RuntimeError("Missing OPENAI_API_KEY, cannot evaluate")

    base_url = os.getenv("OPENAI_BASE_URL") or None
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


def _evaluation_cache_key(topic: str, model: str, record: VideoRecord) -> str:
    subtitle_digest = (
        hashlib.sha1(record.subtitle_text.encode("utf-8")).hexdigest() if record.subtitle_text else "no_subtitle"
    )
    return build_cache_key(topic, model, record.platform, record.video_id, record.title, subtitle_digest)


def _apply_evaluation(record: VideoRecord, parsed: EvaluationResult) -> VideoRecord:
    return record.model_copy(
        update={
            "relevance": parsed.relevance,
            "depth": parsed.depth,
            "clarity": parsed.clarity,
            "has_math": parsed.has_math,
            "has_code": parsed.has_code,
            "audience": parsed.audience,
            "recommend": parsed.recommend,
            "reason": parsed.reason,
        }
    )


async def _evaluate_single_record(
    client,
    model: str,
    topic: str,
    record: VideoRecord,
    semaphore: asyncio.Semaphore,
    retries: int = 2,
    use_cache: bool = True,
) -> VideoRecord:
    cache_key = _evaluation_cache_key(topic, model, record)
    if use_cache:
        cached = load_json_cache("evaluations", cache_key)
        if cached is not None:
            LOGGER.info("Evaluation cache hit: video_id=%s", record.video_id)
            parsed = EvaluationResult.model_validate(cached)
            return _apply_evaluation(record, parsed)

    prompt = load_eval_prompt()
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": _build_user_payload(topic, record)},
    ]

    async with semaphore:
        last_error: Exception | None = None
        for attempt in range(1, retries + 2):
            try:
                LOGGER.info("Evaluation request start: video_id=%s attempt=%s", record.video_id, attempt)
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content or "{}"
                parsed = EvaluationResult.model_validate_json(content)
                if use_cache:
                    save_json_cache("evaluations", cache_key, parsed.model_dump())
                LOGGER.info("Evaluation request success: video_id=%s attempt=%s", record.video_id, attempt)
                return _apply_evaluation(record, parsed)
            except (json.JSONDecodeError, ValidationError, AttributeError, IndexError, TypeError, ValueError) as exc:
                last_error = exc
                LOGGER.warning(
                    "Evaluation parse failed: video_id=%s attempt=%s error=%s", record.video_id, attempt, exc
                )
            except Exception as exc:
                last_error = exc
                LOGGER.warning(
                    "Evaluation request failed: video_id=%s attempt=%s error=%s", record.video_id, attempt, exc
                )
            await asyncio.sleep(min(attempt, 3))

    raise RuntimeError(f"Evaluation failed for {record.video_id}: {last_error}")


async def evaluate_records(
    topic: str,
    records: list[VideoRecord],
    *,
    concurrency: int = 5,
    use_cache: bool = True,
) -> tuple[list[VideoRecord], list[str]]:
    if not records:
        return [], []
    if not evaluation_enabled():
        LOGGER.info("OPENAI_API_KEY not configured, skip evaluation stage")
        return records, []

    client = _create_client()
    model = os.getenv("OPENAI_MODEL", "deepseek-chat")
    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        _evaluate_single_record(client, model, topic, record, semaphore, use_cache=use_cache) for record in records
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    evaluated_records: list[VideoRecord] = []
    errors: list[str] = []
    for record, result in zip(records, results):
        if isinstance(result, Exception):
            message = f"evaluate failed for {record.video_id}: {result}"
            LOGGER.error(message)
            errors.append(message)
            evaluated_records.append(record)
            continue
        evaluated_records.append(result)
    return evaluated_records, errors
