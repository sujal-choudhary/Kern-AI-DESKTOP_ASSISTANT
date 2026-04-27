from core.commands import parse_command


def test_parse_open_app():
    result = parse_command("open notepad")
    assert result == {"task": "open_app", "parameters": {"name": "notepad"}}


def test_parse_whatsapp_send_flow():
    result = parse_command("open whatsapp and send hello to John")
    assert "tasks" in result
    assert result["tasks"][0]["task"] == "open_whatsapp"
    assert result["tasks"][1]["task"] == "send_whatsapp_message"


def test_parse_multi_step_chain():
    result = parse_command("open notepad and then type hello")
    assert "tasks" in result
    assert result["tasks"][0]["task"] == "open_app"
    assert result["tasks"][1]["task"] == "type_text"


def test_parse_close_all_is_safe_chat():
    result = parse_command("close all")
    assert result["task"] == "chat"


def test_parse_youtube_search():
    result = parse_command("search cats on youtube")
    assert "tasks" in result
    assert result["tasks"][0]["task"] == "open_url"
    assert result["tasks"][1]["task"] == "youtube_search"


def test_parse_comma_separated_chain():
    result = parse_command("open notepad, then type hello")
    assert "tasks" in result
    assert result["tasks"][0]["task"] == "open_app"
    assert result["tasks"][1]["task"] == "type_text"
