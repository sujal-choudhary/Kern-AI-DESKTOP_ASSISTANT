import secrets
import subprocess
import threading
import time
import hmac
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from config import ENABLE_POWERSHELL, POWERSHELL_CONFIRM_PASSPHRASE, POWERSHELL_TIMEOUT_SECONDS


RISKY_KEYWORDS = (
    "remove-item",
    "del ",
    "erase ",
    "format ",
    "reg delete",
    "bcdedit",
    "diskpart",
    "shutdown",
    "restart-computer",
    "stop-computer",
    "taskkill /f",
    "cipher /w",
)


def is_risky_powershell(command: str) -> bool:
    lowered = command.lower().strip()
    return any(keyword in lowered for keyword in RISKY_KEYWORDS)


@dataclass
class PendingPowerShell:
    command: str
    risky: bool
    created_at: float


class PowerShellConfirmManager:
    def __init__(self) -> None:
        self._pending: Dict[str, PendingPowerShell] = {}
        self._lock = threading.Lock()
        self._ttl_seconds = 300

    def _cleanup_expired(self) -> None:
        now = time.time()
        self._pending = {
            nonce: pending
            for nonce, pending in self._pending.items()
            if now - pending.created_at < self._ttl_seconds
        }

    def create_pending(self, command: str) -> Tuple[str, PendingPowerShell]:
        with self._lock:
            self._cleanup_expired()
            nonce = secrets.token_hex(12)
            pending = PendingPowerShell(command=command, risky=is_risky_powershell(command), created_at=time.time())
            self._pending[nonce] = pending
            return nonce, pending

    def get(self, nonce: str) -> Optional[PendingPowerShell]:
        with self._lock:
            self._cleanup_expired()
            return self._pending.get(nonce)

    def pop(self, nonce: str) -> Optional[PendingPowerShell]:
        with self._lock:
            self._cleanup_expired()
            return self._pending.pop(nonce, None)

    def list_pending(self) -> Dict[str, Dict[str, str]]:
        out: Dict[str, Dict[str, str]] = {}
        with self._lock:
            self._cleanup_expired()
            for nonce, item in self._pending.items():
                out[nonce] = {"command": item.command, "risky": str(item.risky).lower()}
        return out


def run_powershell(command: str) -> Dict[str, str]:
    if not ENABLE_POWERSHELL:
        return {
            "ok": "false",
            "message": "PowerShell mode is disabled. Set KARN_ENABLE_POWERSHELL=true (or legacy MENU_ENABLE_POWERSHELL=true) to enable.",
        }

    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command],
        capture_output=True,
        text=True,
        timeout=POWERSHELL_TIMEOUT_SECONDS,
    )
    output = (completed.stdout or "").strip()
    error = (completed.stderr or "").strip()
    if completed.returncode == 0:
        return {"ok": "true", "message": output or "PowerShell command completed.", "stdout": output, "stderr": error}
    return {"ok": "false", "message": error or "PowerShell command failed.", "stdout": output, "stderr": error}


def confirm_allowed(pending: PendingPowerShell, passphrase: str) -> Tuple[bool, str]:
    if pending.risky:
        if not POWERSHELL_CONFIRM_PASSPHRASE:
            return False, "Risky command blocked because KARN_POWERSHELL_PASSPHRASE (or legacy MENU_POWERSHELL_PASSPHRASE) is not set."
        if not hmac.compare_digest(passphrase, POWERSHELL_CONFIRM_PASSPHRASE):
            return False, "Incorrect passphrase for risky command."
    return True, "Confirmed."

