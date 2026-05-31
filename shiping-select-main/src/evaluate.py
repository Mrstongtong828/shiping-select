from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

from pydantic import ValidationError

from src.schema import EvaluationResult, VideoRecord


PROMPT_PATH = Path("prompts/eval_template.txt")
LOGGER = logging.getLogger("video_finder")


def load_eval_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def evaluation_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


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
        raise RuntimeError("缺少 openai 依赖，请先安装 requirements.txt") from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 OPENAI_API_KEY，无法执行评估")

    base_url = os.getenv("OPENAI_BASE_URL") or None
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


async def _evaluate_single_record(
    client,
    model: str,
    topic: str,
    record: VideoRecord,
    semaphore: asyncio.Semaphore,
    retries: int = 2,
) -> VideoRecord:
    prompt = load_eval_prompt()
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": _build_user_payload(topic, record)},
    ]

    async with semaphore:
        last_error: Exception | None = None
        for attempt in range(1, retries + 2):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content or "{}"
                parsed = EvaluationResult.model_validate_json(content)
                updated = record.model_copy(
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
                return updated
            except (json.JSONDecodeError, ValidationError, AttributeError, IndexError, TypeError, ValueError) as exc:
                last_error = exc
                LOGGER.warning("评估结果解析失败: video_id=%s attempt=%s error=%s", record.video_id, attempt, exc)
            except Exception as exc:
                last_error = exc
                LOGGER.warning("评估调用失败: video_id=%s attempt=%s error=%s", record.video_id, attempt, exc)
            await asyncio.sleep(min(attempt, 3))

    raise RuntimeError(f"评估失败 video_id={record.video_id}: {last_error}")


async def evaluate_records(
    topic: str,
    records: list[VideoRecord],
    *,
    concurrency: int = 5,
) -> tuple[list[VideoRecord], list[str]]:
    if not records:
        return [], []
    if not evaluation_enabled():
        LOGGER.info("未配置 OPENAI_API_KEY，跳过评估阶段")
        return records, []

    client = _create_client()
    model = os.getenv("OPENAI_MODEL", "deepseek-chat")
    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        _evaluate_single_record(client, model, topic, record, semaphore)
        for record in records
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
