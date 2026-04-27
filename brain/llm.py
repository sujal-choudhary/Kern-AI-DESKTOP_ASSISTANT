import json
import logging
import re
import threading
import time
from typing import Any, Dict, List

import ollama

from config import LLM_HISTORY_TURNS, LLM_NUM_CTX, MODEL

VALID_TASKS = {
    "create_folder",
    "delete_folder",
    "create_file",
    "open_file",
    "read_file",
    "write_file",
    "append_file",
    "delete_file",
    "search_file",
    "list_files",
    "open_app",
    "open_url",
    "close_app",
    "open_folder",
    "type_text",
    "press_key",
    "hotkey",
    "click_on_text",
    "click_at",
    "open_whatsapp",
    "send_whatsapp_message",
    "check_emails",
    "read_screen",
    "summarize_screen",
    "extract_emails_from_screen",
    "autofill_form",
    "take_screenshot",
    "youtube_search",
    "play_in_youtube",
    "google_search",
    "wikipedia_search",
    "wikipedia_summary",
    "amazon_search",
    "hotstar_search",
    "spotify_search",
    "linkedin_search",
    "github_search",
    "twitter_search",
    "google_news_search",
    "maps_search",
    "pypi_search",
    "gaana_search",
    "get_current_time",
    "greet",
    "run_powershell",
}

SYSTEM_PROMPT = """You are Karn, a desktop assistant.
Return STRICT JSON only for actions:
{"task":"name","parameters":{}}
or
{"tasks":[{"task":"name","parameters":{}},...]}
For casual chat:
{"task":"chat","parameters":{"message":"..."}}
Never use markdown code fences."""

_RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}
_MAX_CACHE_ITEMS = 64
_CACHE_TTL_SECONDS = 3600
_CACHE_LOCK = threading.Lock()


def _strip_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return cleaned.strip()


def _chat_message(message: str) -> Dict[str, Any]:
    return {"task": "chat", "parameters": {"message": message}}


def _normalize_task(item: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("Task payload must be an object")
    task = item.get("task")
    parameters = item.get("parameters", {})
    if not isinstance(task, str):
        raise ValueError("Task missing valid name")
    if task != "chat" and task not in VALID_TASKS:
        raise ValueError(f"Unsupported task: {task}")
    if not isinstance(parameters, dict):
        raise ValueError("Task parameters must be an object")
    return {"task": task, "parameters": parameters}


def normalize_llm_output(raw_reply: str) -> Dict[str, Any]:
    payload = _strip_fences(raw_reply)
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        # Try to extract the first JSON object from mixed output
        match = re.search(r"\{[\s\S]*\}", payload)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                # If it looks like a JSON tool-call but is malformed, don't speak the raw JSON.
                if '"task"' in payload or '"tasks"' in payload or payload.strip().startswith("{"):
                    return _chat_message("I generated an invalid action payload, so I did not execute it.")
                return _chat_message(raw_reply.strip())
        else:
            if '"task"' in payload or '"tasks"' in payload or payload.strip().startswith("{"):
                return _chat_message("I generated an invalid action payload, so I did not execute it.")
            return _chat_message(raw_reply.strip())

    if not isinstance(parsed, dict):
        return _chat_message(raw_reply.strip())

    if "tasks" in parsed:
        tasks = parsed.get("tasks")
        if not isinstance(tasks, list):
            return _chat_message("I understood your request but generated an invalid task list.")
        normalized: List[Dict[str, Any]] = []
        for item in tasks:
            try:
                normalized.append(_normalize_task(item))
            except ValueError as exc:
                logging.warning("Dropped invalid task from LLM output: %s", exc)
        if not normalized:
            return _chat_message("I could not generate a safe action plan for that request.")
        return {"tasks": normalized}

    if "task" in parsed:
        try:
            return _normalize_task(parsed)
        except ValueError as exc:
            logging.warning("Invalid single task from LLM output: %s", exc)
            return _chat_message("I generated an invalid action, so I did not execute it.")

    return _chat_message(raw_reply.strip())


def get_response(prompt: str, conversation_history: List[Dict[str, str]] | None = None) -> Dict[str, Any]:
    """Get and normalize response from Ollama."""
    try:
        cache_key = prompt.strip().lower()
        with _CACHE_LOCK:
            cached = _RESPONSE_CACHE.get(cache_key)
            if cached:
                cached_at = cached.get("_cached_at", 0.0)
                if isinstance(cached_at, (int, float)) and (time.time() - float(cached_at) < _CACHE_TTL_SECONDS):
                    return {k: v for k, v in cached.items() if k != "_cached_at"}
                _RESPONSE_CACHE.pop(cache_key, None)

        messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if conversation_history:
            max_history_messages = max(0, LLM_HISTORY_TURNS * 2)
            messages.extend(conversation_history[-max_history_messages:])
        messages.append({"role": "user", "content": prompt})
        response = None
        for attempt in range(3):
            try:
                response = ollama.chat(
                    model=MODEL,
                    messages=messages,
                    options={"num_ctx": LLM_NUM_CTX, "temperature": 0.2},
                )
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(0.4 * (2**attempt))
        assert response is not None
        raw_reply = response["message"]["content"]
        normalized = normalize_llm_output(raw_reply)
        with _CACHE_LOCK:
            _RESPONSE_CACHE[cache_key] = {**normalized, "_cached_at": time.time()}
            if len(_RESPONSE_CACHE) > _MAX_CACHE_ITEMS:
                oldest_key = next(iter(_RESPONSE_CACHE))
                _RESPONSE_CACHE.pop(oldest_key, None)
        return normalized
    except Exception as exc:
        logging.error("Error getting response: %s", exc)
        return _chat_message("Sorry, I encountered an error while processing that request.")