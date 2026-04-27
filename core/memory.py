import json
import threading
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List

from config import MEMORY_STORE_PATH


class MemoryStore:
    """Persistent interaction memory for cross-session context."""

    def __init__(self, path: str = MEMORY_STORE_PATH, max_items: int = 200) -> None:
        self.path = Path(path)
        self.max_items = max_items
        self._lock = threading.Lock()
        self._data: Dict[str, List[Dict[str, str]]] = {"interactions": []}
        self._load()

    def _load(self) -> None:
        with self._lock:
            if not self.path.exists():
                return
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(loaded, dict) or "interactions" not in loaded or not isinstance(loaded["interactions"], list):
                    self._data = {"interactions": []}
                else:
                    self._data = {"interactions": loaded["interactions"][-self.max_items :]}
            except Exception:
                self._data = {"interactions": []}

    def _save(self) -> None:
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        temp_path.replace(self.path)

    def add_interaction(self, user_text: str, assistant_text: str) -> None:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user": user_text,
            "assistant": assistant_text,
        }
        with self._lock:
            self._data["interactions"].append(entry)
            self._data["interactions"] = self._data["interactions"][-self.max_items :]
            self._save()

    def get_recent_as_history(self, turns: int = 6) -> List[Dict[str, str]]:
        with self._lock:
            interactions = self._data["interactions"][-turns:]
        history: List[Dict[str, str]] = []
        for item in interactions:
            history.append({"role": "user", "content": item["user"]})
            history.append({"role": "assistant", "content": item["assistant"]})
        return history

    def get_recent_entries(self, limit: int = 20) -> List[Dict[str, str]]:
        with self._lock:
            return list(self._data["interactions"][-limit:])
