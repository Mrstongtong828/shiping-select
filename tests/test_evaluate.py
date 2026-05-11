from src.evaluate import load_eval_prompt


def test_load_eval_prompt_contains_required_fields():
    prompt = load_eval_prompt()
    assert "relevance" in prompt
    assert "reason" in prompt

