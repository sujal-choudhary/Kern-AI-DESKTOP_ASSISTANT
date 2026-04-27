from core.learned_commands import LearnedCommandsStore


def test_learned_command_store(tmp_path):
    store_path = tmp_path / "learned.json"
    store = LearnedCommandsStore(path=store_path)
    store.teach("clean desktop", "delete temp files")
    assert store.resolve("clean desktop") == "delete temp files"

    reloaded = LearnedCommandsStore(path=store_path)
    assert reloaded.resolve("clean desktop") == "delete temp files"
