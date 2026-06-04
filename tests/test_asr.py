import sys
import types

import pytest

from src import asr_whisper
from src.schema import SubtitlePayload, VideoRecord


@pytest.mark.asyncio
async def test_fill_record_subtitle_with_asr_updates_empty_subtitle(monkeypatch):
    record = VideoRecord(
        platform="youtube",
        video_id="video-1",
        title="PCA tutorial",
        url="https://www.youtube.com/watch?v=video-1",
    )

    async def fake_generate_subtitle_with_asr(record, subtitle_limit=6000):
        return SubtitlePayload(text="ASR transcript", language="en", source="whisper_asr")

    monkeypatch.setattr(asr_whisper, "generate_subtitle_with_asr", fake_generate_subtitle_with_asr)

    updated = await asr_whisper.fill_record_subtitle_with_asr(record)

    assert updated.has_subtitle is True
    assert updated.subtitle_text == "ASR transcript"
    assert updated.subtitle_language == "en"
    assert updated.subtitle_source == "whisper_asr"


def test_transcribe_audio_uses_cpu_device_by_default(monkeypatch, tmp_path):
    captured = {}

    class FakeWhisperModel:
        def __init__(self, model_name, *, device, compute_type):
            captured["model_name"] = model_name
            captured["device"] = device
            captured["compute_type"] = compute_type

        def transcribe(self, audio_path, vad_filter):
            segment = types.SimpleNamespace(text="hello asr")
            info = types.SimpleNamespace(language="en")
            return [segment], info

    fake_module = types.SimpleNamespace(WhisperModel=FakeWhisperModel)
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)
    monkeypatch.delenv("ASR_DEVICE", raising=False)
    monkeypatch.delenv("ASR_MODEL", raising=False)
    monkeypatch.delenv("ASR_COMPUTE_TYPE", raising=False)

    subtitle = asr_whisper._transcribe_audio_sync(tmp_path / "audio.webm", subtitle_limit=20)

    assert subtitle.text == "hello asr"
    assert captured == {
        "model_name": "small",
        "device": "cpu",
        "compute_type": "int8",
    }
