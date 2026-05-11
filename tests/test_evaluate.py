from src.evaluate import evaluation_enabled, load_eval_prompt


def test_load_eval_prompt_contains_required_fields():
    prompt = load_eval_prompt()
    assert "relevance" in prompt
    assert "reason" in prompt
    assert "recommend" in prompt


def test_evaluation_enabled_defaults_to_boolean():
    assert isinstance(evaluation_enabled(), bool)
