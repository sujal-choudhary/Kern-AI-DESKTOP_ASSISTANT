from brain.llm import normalize_llm_output


def test_normalize_markdown_wrapped_json():
    raw = """```json
{"task":"open_app","parameters":{"name":"notepad"}}
```"""
    result = normalize_llm_output(raw)
    assert result["task"] == "open_app"
    assert result["parameters"]["name"] == "notepad"


def test_invalid_task_falls_back_to_chat():
    raw = '{"task":"drop_database","parameters":{}}'
    result = normalize_llm_output(raw)
    assert result["task"] == "chat"


def test_new_tasks_are_allowed():
    raw = '{"task":"youtube_search","parameters":{"query":"cats"}}'
    result = normalize_llm_output(raw)
    assert result["task"] == "youtube_search"
