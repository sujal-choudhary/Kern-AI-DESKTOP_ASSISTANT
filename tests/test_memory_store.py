from core.memory import MemoryStore


def test_memory_store_persists(tmp_path):
    db_path = tmp_path / "memory.json"
    store = MemoryStore(path=str(db_path), max_items=5)
    store.add_interaction("hello", "hi")

    reloaded = MemoryStore(path=str(db_path), max_items=5)
    entries = reloaded.get_recent_entries(limit=5)
    assert len(entries) == 1
    assert entries[0]["user"] == "hello"
    assert entries[0]["assistant"] == "hi"
