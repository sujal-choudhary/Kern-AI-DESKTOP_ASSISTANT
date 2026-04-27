from web_panel import app


def test_status_endpoint():
    client = app.test_client()
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "voice_enabled" in data
    assert "recent_memory" in data
    assert "learned_commands" in data


def test_command_endpoint_requires_command():
    client = app.test_client()
    resp = client.post("/api/command", json={})
    assert resp.status_code == 400

