import logging
import re
import threading
import time
from typing import Any, Dict, List

from brain.llm import get_response
from core.actions import execute_task
from core.commands import parse_command
from core.memory import MemoryStore
from core.learned_commands import LearnedCommandsStore
from core.powershell_mode import PowerShellConfirmManager, confirm_allowed, run_powershell
from core.stt import clear_transcript, get_live_state, listen, start_offline_stt, stop_offline_stt
from core.tts import speak


class AssistantService:
    def __init__(self) -> None:
        self.conversation_history: List[Dict[str, str]] = []
        self.memory = MemoryStore()
        self.learned_commands = LearnedCommandsStore()
        self._voice_enabled_event = threading.Event()
        self.powershell = PowerShellConfirmManager()
        self._voice_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._last_voice_command = ""
        self._last_voice_command_at = 0.0

    def _message_from_result(self, result: Dict[str, Any]) -> str:
        return result.get("message", "Done.")

    @property
    def voice_enabled(self) -> bool:
        return self._voice_enabled_event.is_set()

    def _run_payload(self, payload: Dict[str, Any]) -> str:
        if payload.get("task") == "chat":
            return payload.get("parameters", {}).get("message", "I am here.")

        if "tasks" in payload:
            messages: List[str] = []
            for item in payload["tasks"]:
                result = execute_task(item["task"], item.get("parameters", {}))
                logging.info("Executed task %s -> %s", item["task"], result)
                messages.append(self._message_from_result(result))
            return "; ".join(messages)

        result = execute_task(payload["task"], payload.get("parameters", {}))
        logging.info("Executed task %s -> %s", payload["task"], result)
        return self._message_from_result(result)

    def _should_ignore_voice_command(self, command: str) -> bool:
        cleaned = (command or "").strip().lower()
        if not cleaned:
            return True
        if cleaned in {"listening", "listening...", "processing", "still processing"}:
            return True
        if len(cleaned) < 2:
            return True

        # Ignore immediate duplicates often produced by STT repetitions.
        now = time.time()
        if cleaned == self._last_voice_command and (now - self._last_voice_command_at) < 2.5:
            return True
        self._last_voice_command = cleaned
        self._last_voice_command_at = now
        return False

    def handle_text_command(self, command: str, speak_response: bool = False) -> str:
        with self._lock:
            confirm_match = re.search(r"^confirm\s+([a-fA-F0-9]{24})(?:\s+(.+))?$", command.strip(), re.IGNORECASE)
            if confirm_match:
                nonce = confirm_match.group(1)
                passphrase = (confirm_match.group(2) or "").strip()
                pending = self.powershell.pop(nonce)
                if not pending:
                    response_message = f"No pending command found for id {nonce}."
                else:
                    allowed, reason = confirm_allowed(pending, passphrase)
                    if not allowed:
                        response_message = reason
                    else:
                        result = run_powershell(pending.command)
                        response_message = result.get("message", "PowerShell command completed.")
                self.memory.add_interaction(command, response_message)
                if speak_response:
                    speak(response_message)
                return response_message

            ps_match = re.search(r"^(?:powershell|ps)\s*:\s*(.+)$", command.strip(), re.IGNORECASE)
            if ps_match:
                cmd = ps_match.group(1).strip()
                nonce, pending = self.powershell.create_pending(cmd)
                if pending.risky:
                    response_message = (
                        f"PowerShell command is RISKY and requires confirmation.\n"
                        f"To run: confirm {nonce} <passphrase>"
                    )
                else:
                    response_message = (
                        f"PowerShell command is ready.\n"
                        f"To run: confirm {nonce}"
                    )
                self.memory.add_interaction(command, response_message)
                if speak_response:
                    speak(response_message)
                return response_message

            teach_match = re.search(
                r"when i say (.+?)[, ]+(?:do|run)?\s*(.+)$",
                command.strip(),
                re.IGNORECASE,
            )
            if teach_match:
                trigger = teach_match.group(1).strip().strip("'\"")
                mapped = teach_match.group(2).strip().strip("'\"")
                self.learned_commands.teach(trigger, mapped)
                response_message = f"Learned. Next time you say '{trigger}', I will run: {mapped}"
                self.memory.add_interaction(command, response_message)
                if speak_response:
                    speak(response_message)
                return response_message

            learned_mapped = self.learned_commands.resolve(command)
            if learned_mapped:
                command = learned_mapped

            parsed = parse_command(command)
            if parsed is None and len(command.strip().split()) <= 2:
                response_message = "I could not understand that clearly. Please repeat the command in a short full phrase."
                self.memory.add_interaction(command, response_message)
                if speak_response:
                    speak(response_message)
                return response_message
            memory_context = self.memory.get_recent_as_history(turns=6)
            merged_history = memory_context + self.conversation_history
            payload = parsed if parsed is not None else get_response(command, conversation_history=merged_history)
            response_message = self._run_payload(payload)
            self.conversation_history.append({"role": "user", "content": command})
            self.conversation_history.append({"role": "assistant", "content": response_message})
            self.conversation_history = self.conversation_history[-20:]
            self.memory.add_interaction(command, response_message)

        if speak_response:
            speak(response_message)
        return response_message

    def _voice_loop(self) -> None:
        speak("Voice mode enabled.")
        # Start offline STT system
        if not start_offline_stt():
            speak("Failed to start offline speech recognition.")
            self._voice_enabled_event.clear()
            return

        try:
            while self.voice_enabled:
                command = listen()
                if not command:
                    continue
                if self._should_ignore_voice_command(command):
                    continue
                lowered = command.lower()
                if "exit voice" in lowered or "stop listening" in lowered:
                    self._voice_enabled_event.clear()
                    break
                self.handle_text_command(command, speak_response=True)
        finally:
            # Always stop STT system
            stop_offline_stt()
            clear_transcript()
        speak("Voice mode disabled.")

    def start_voice(self) -> bool:
        with self._lock:
            if self.voice_enabled:
                return False
            self._voice_enabled_event.set()
            self._voice_thread = threading.Thread(target=self._voice_loop, daemon=True)
            self._voice_thread.start()
            return True

    def stop_voice(self) -> bool:
        with self._lock:
            if not self.voice_enabled:
                return False
            self._voice_enabled_event.clear()
            return True

    def status(self) -> Dict[str, Any]:
        return {
            "voice_enabled": self.voice_enabled,
            "stt_live": get_live_state(),
            "recent_memory": self.memory.get_recent_entries(limit=10),
            "learned_commands": self.learned_commands.list_commands(),
            "pending_powershell": self.powershell.list_pending(),
        }


assistant_service = AssistantService()
