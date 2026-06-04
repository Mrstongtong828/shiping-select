from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path

from src.schema import SubtitlePayload, VideoRecord

LOGGER = logging.getLogger("video_finder")


def _download_audio_sync(url: str, workdir: str) -> Path:
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise RuntimeError("Missing yt-dlp dependency for ASR fallback") from exc

    output_template = str(Path(workdir) / "audio.%(ext)s")
    options = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        downloaded_path = ydl.prepare_filename(info)
    return Path(downloaded_path)


def _transcribe_audio_sync(audio_path: Path, subtitle_limit: int) -> SubtitlePayload:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Missing faster-whisper dependency for ASR fallback") from exc

    model_name = os.getenv("ASR_MODEL", "small")
    compute_type = os.getenv("ASR_COMPUTE_TYPE", "int8")
    device = os.getenv("ASR_DEVICE", "cpu")
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments, info = model.transcribe(str(audio_path), vad_filter=True)
    text = "\n".join(segment.text.strip() for segment in segments if segment.text).strip()
    return SubtitlePayload(
        text=text[:subtitle_limit],
        language=getattr(info, "language", "") or "",
        source="whisper_asr",
    )


async def generate_subtitle_with_asr(record: VideoRecord, subtitle_limit: int = 6000) -> SubtitlePayload:
    with tempfile.TemporaryDirectory(prefix="video_finder_asr_") as tmpdir:
        audio_path = await asyncio.to_thread(_download_audio_sync, record.url, tmpdir)
        try:
            return await asyncio.to_thread(_transcribe_audio_sync, audio_path, subtitle_limit)
        finally:
            try:
                if audio_path.exists():
                    audio_path.unlink()
            except OSError:
                LOGGER.warning("Failed to remove temporary audio file: %s", audio_path)


async def fill_record_subtitle_with_asr(record: VideoRecord, subtitle_limit: int = 6000) -> VideoRecord:
    subtitle = await generate_subtitle_with_asr(record, subtitle_limit=subtitle_limit)
    if not subtitle.text:
        return record
    return record.model_copy(
        update={
            "has_subtitle": True,
            "subtitle_text": subtitle.text,
            "subtitle_language": subtitle.language,
            "subtitle_source": subtitle.source,
        }
    )
