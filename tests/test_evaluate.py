from src.evaluate import evaluation_enabled, load_eval_prompt


def test_load_eval_prompt_contains_required_fields():
    prompt = load_eval_prompt()
    assert "relevance" in prompt
    assert "reason" in prompt
    assert "recommend" in prompt


def test_evaluation_enabled_defaults_to_boolean():
    assert isinstance(evaluation_enabled(), bool)


def test_evaluation_enabled_rejects_placeholder_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "your_openai_compatible_api_key")

    assert evaluation_enabled() is False


def test_evaluation_enabled_accepts_real_key_shape(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-value")

    assert evaluation_enabled() is True
