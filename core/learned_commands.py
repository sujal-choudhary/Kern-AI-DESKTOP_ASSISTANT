import json
import threading
from pathlib import Path
from typing import Dict, Optional

from config import BASE_DIR

LEARNED_COMMANDS_PATH = Path(BASE_DIR) / "learned_commands.json"


class LearnedCommandsStore:
    def __init__(self, path: Path = LEARNED_COMMANDS_PATH) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._commands: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._commands = {str(k).strip().lower(): str(v).strip() for k, v in data.items()}
        except Exception:
            self._commands = {}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._commands, indent=2), encoding="utf-8")

    def teach(self, trigger: str, action_command: str) -> None:
        key = trigger.strip().lower()
        if not key or not action_command.strip():
            raise ValueError("Trigger and action command are required")
        with self._lock:
            self._commands[key] = action_command.strip()
            self._save()

    def resolve(self, command: str) -> Optional[str]:
        return self._commands.get(command.strip().lower())

    def list_commands(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._commands)
