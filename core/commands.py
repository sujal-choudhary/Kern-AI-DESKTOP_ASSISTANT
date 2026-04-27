import re
from typing import Any, Dict, Optional


def _single(task: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"task": task, "parameters": parameters or {}}


_STEP_DELIMITERS = (
    " and then ",
    " then ",
    " after that ",
    " next ",
    " also ",
    " and ",
    ",",
    ";",
)


def _normalize_leading_phrase(text: str) -> str:
    lowered = text.lower().strip()
    for prefix in ("karn ", "hey karn ", "menu ", "hey menu ", "please ", "can you ", "could you ", "will you "):
        if lowered.startswith(prefix):
            text = text[len(prefix) :]
            lowered = text.lower().strip()
    return text.strip()


def _split_steps(command: str) -> list[str]:
    normalized = _normalize_leading_phrase(command)
    tmp = normalized
    for d in _STEP_DELIMITERS:
        if d in (",", ";"):
            tmp = tmp.replace(d, " then ")
        else:
            tmp = re.sub(re.escape(d), " then ", tmp, flags=re.IGNORECASE)
    steps = [s.strip() for s in re.split(r"\bthen\b", tmp, flags=re.IGNORECASE) if s.strip()]
    return steps


def _parse_single(command: str) -> Optional[Dict[str, Any]]:
    lowered = command.lower().strip()
    if not lowered:
        return None

    if lowered in ("close all", "close all apps", "close everything"):
        return _single("chat", {"message": "I can’t safely close ALL apps at once. Tell me which app to close (e.g., 'close chrome')."})

    if lowered.startswith("take screenshot") or lowered.startswith("screenshot"):
        return _single("take_screenshot")

    if "what is the time" in lowered or "current time" in lowered or lowered == "time":
        return _single("get_current_time")

    yt_match = re.search(r"(?:search|find)\s+(.+?)\s+(?:on|in)\s+youtube$", lowered)
    if yt_match:
        query = yt_match.group(1).strip().strip("'\"")
        return {"tasks": [_single("open_url", {"url": "https://www.youtube.com"}), _single("youtube_search", {"query": query})]}

    play_yt_match = re.search(r"(?:play)\s+(.+?)\s+(?:on|in)\s+youtube$", lowered)
    if play_yt_match:
        query = play_yt_match.group(1).strip().strip("'\"")
        return _single("play_in_youtube", {"query": query})

    if lowered.startswith("open a "):
        lowered = "open " + lowered[7:]
        command = "open " + command.strip()[7:]
    if lowered.startswith("open the "):
        lowered = "open " + lowered[9:]
        command = "open " + command.strip()[9:]

    if lowered.startswith("open youtube") or lowered == "youtube":
        return _single("open_url", {"url": "https://www.youtube.com"})

    if lowered.startswith("open google"):
        return _single("open_url", {"url": "https://www.google.com"})

    if lowered.startswith("open stackoverflow"):
        return _single("open_url", {"url": "https://stackoverflow.com"})

    if lowered.startswith("open desktop panel") or lowered.startswith("open web panel"):
        return _single("open_url", {"url": "http://127.0.0.1:5000"})

    if "open whatsapp" in lowered and "send" in lowered and " to " in lowered:
        send_match = re.search(r"send (.+?) to (.+)$", command, re.IGNORECASE)
        if send_match:
            message = send_match.group(1).strip().strip("'\"")
            contact = send_match.group(2).strip().strip("'\"")
            return {
                "tasks": [
                    _single("open_whatsapp"),
                    _single("send_whatsapp_message", {"contact": contact, "message": message}),
                ]
            }

    if "open whatsapp" in lowered:
        return _single("open_whatsapp")

    if (
        lowered.startswith("open ")
        and "file" not in lowered
        and "folder" not in lowered
        and " and " not in lowered
        and " then " not in lowered
    ):
        app = command[5:].strip()
        return _single("open_app", {"name": app})

    if lowered.startswith("close "):
        app = command[6:].strip()
        return _single("close_app", {"name": app})

    if "create folder" in lowered or "make folder" in lowered:
        match = re.search(r"folder(?: named)? ([\w\-. ]+)", command, re.IGNORECASE)
        if match:
            return _single("create_folder", {"path": "", "name": match.group(1).strip()})

    if "create file" in lowered:
        match = re.search(r"file(?: named)? ([\w\-. ]+)", command, re.IGNORECASE)
        if match:
            return _single("create_file", {"path": "", "name": match.group(1).strip(), "content": ""})

    if "delete folder" in lowered:
        match = re.search(r"folder ([\w\-./ ]+)", command, re.IGNORECASE)
        if match:
            return _single("delete_folder", {"path": match.group(1).strip()})

    if "read file" in lowered:
        match = re.search(r"file ([\w\-./ ]+)", command, re.IGNORECASE)
        if match:
            return _single("read_file", {"path": match.group(1).strip()})

    if "write" in lowered and "file" in lowered and ":" in command:
        parts = command.split(":", 1)
        match = re.search(r"file ([\w\-./ ]+)", parts[0], re.IGNORECASE)
        if match:
            return _single("write_file", {"path": match.group(1).strip(), "content": parts[1].strip()})

    if lowered.startswith("type "):
        return _single("type_text", {"text": command[5:].strip()})

    if lowered.startswith("click on "):
        return _single("click_on_text", {"text": command[9:].strip()})

    click_match = re.search(r"click at (\d+)[, ]+(\d+)", lowered)
    if click_match:
        return _single("click_at", {"x": int(click_match.group(1)), "y": int(click_match.group(2))})

    if "summarize this page" in lowered or "summarize screen" in lowered:
        return _single("summarize_screen")

    if "extract all emails" in lowered or "extract emails" in lowered:
        return _single("extract_emails_from_screen")

    if "what is this" in lowered:
        return _single("summarize_screen")

    if "fill this form" in lowered or "apply for this job" in lowered:
        return _single("autofill_form")

    if "check email" in lowered or "open gmail" in lowered:
        return _single("check_emails")

    # Music-related commands
    music_search_match = re.search(r"(?:play|search|find)\s+(?:song|music|track)?\s*(.+?)(?:\s+on\s+(?:spotify|youtube))?$", lowered)
    if music_search_match:
        song = music_search_match.group(1).strip().strip("'\"")
        # Default to YouTube for music
        return {
            "tasks": [
                _single("open_url", {"url": "https://www.youtube.com"}),
                _single("youtube_search", {"query": f"{song} music"})
            ]
        }

    if lowered.startswith("play "):
        song = command[5:].strip()
        return {
            "tasks": [
                _single("open_url", {"url": "https://www.youtube.com"}),
                _single("youtube_search", {"query": f"{song} music"})
            ]
        }

    # Google search patterns
    google_match = re.search(r"(?:google|search)\s+(?:for\s+)?(.+?)$", lowered)
    if google_match and not any(platform in lowered for platform in ["youtube", "amazon", "wikipedia", "hotstar", "spotify", "linkedin", "github", "twitter", "wiki"]):
        query = google_match.group(1).strip().strip("'\"")
        return _single("google_search", {"query": query})

    # Wikipedia search patterns
    wiki_match = re.search(r"(?:wiki|wikipedia)\s+(?:search\s+for\s+)?(.+?)$", lowered)
    if wiki_match:
        query = wiki_match.group(1).strip().strip("'\"")
        return _single("wikipedia_search", {"query": query})

    wiki_summary_match = re.search(r"(?:who is|what is|tell me about)\s+(.+?)\s*(?:from wikipedia|on wikipedia)?$", lowered)
    if wiki_summary_match and "wikipedia" in lowered:
        query = wiki_summary_match.group(1).strip().strip("'\"")
        return _single("wikipedia_summary", {"query": query})

    # Amazon search patterns
    amazon_match = re.search(r"(?:amazon|search\s+amazon)\s+(?:for\s+)?(.+?)$", lowered)
    if amazon_match:
        query = amazon_match.group(1).strip().strip("'\"")
        return _single("amazon_search", {"query": query})

    # Hotstar search patterns
    hotstar_match = re.search(r"(?:hotstar|search\s+hotstar)\s+(?:for\s+)?(.+?)$", lowered)
    if hotstar_match:
        query = hotstar_match.group(1).strip().strip("'\"")
        return _single("hotstar_search", {"query": query})

    # Spotify search patterns
    spotify_match = re.search(r"(?:spotify|search\s+spotify)\s+(?:for\s+)?(.+?)$", lowered)
    if spotify_match:
        query = spotify_match.group(1).strip().strip("'\"")
        return _single("spotify_search", {"query": query})

    # LinkedIn search patterns
    linkedin_match = re.search(r"(?:linkedin|search\s+linkedin)\s+(?:for\s+)?(.+?)$", lowered)
    if linkedin_match:
        query = linkedin_match.group(1).strip().strip("'\"")
        return _single("linkedin_search", {"query": query})

    # GitHub search patterns
    github_match = re.search(r"(?:github|search\s+github)\s+(?:for\s+)?(.+?)$", lowered)
    if github_match:
        query = github_match.group(1).strip().strip("'\"")
        return _single("github_search", {"query": query})

    # Twitter search patterns
    twitter_match = re.search(r"(?:twitter|search\s+twitter)\s+(?:for\s+)?(.+?)$", lowered)
    if twitter_match:
        query = twitter_match.group(1).strip().strip("'\"")
        return _single("twitter_search", {"query": query})

    # Google News search patterns
    news_match = re.search(r"(?:news|google\s+news)\s+(?:search\s+)?(?:for\s+)?(.+?)$", lowered)
    if news_match:
        query = news_match.group(1).strip().strip("'\"")
        return _single("google_news_search", {"query": query})

    # Google Maps search patterns
    maps_match = re.search(r"(?:maps?|find\s+on\s+maps?|search\s+maps?)\s+(?:for\s+)?(.+?)$", lowered)
    if maps_match:
        query = maps_match.group(1).strip().strip("'\"")
        return _single("maps_search", {"query": query})

    # PyPI search patterns
    pypi_match = re.search(r"(?:pypi|python\s+package)\s+(?:search\s+)?(?:for\s+)?(.+?)$", lowered)
    if pypi_match:
        query = pypi_match.group(1).strip().strip("'\"")
        return _single("pypi_search", {"query": query})

    # Gaana music search patterns
    gaana_match = re.search(r"(?:gaana|search\s+gaana)\s+(?:for\s+)?(.+?)$", lowered)
    if gaana_match:
        query = gaana_match.group(1).strip().strip("'\"")
        return _single("gaana_search", {"query": query})

    return None


def parse_command(command: str) -> Optional[Dict[str, Any]]:
    """Fast deterministic parser for common commands before LLM fallback."""
    command = _normalize_leading_phrase(command or "")
    if not command or len(command) > 1000:
        return None

    # Keep single-command parsing first (important for WhatsApp multi-step parsing).
    direct = _parse_single(command)
    if direct is not None:
        return direct

    steps = _split_steps(command)
    if len(steps) <= 1:
        return None

    tasks = []
    for step in steps:
        parsed_part = _parse_single(step)
        if not parsed_part:
            return None
        if "tasks" in parsed_part:
            tasks.extend(parsed_part["tasks"])
        else:
            tasks.append(parsed_part)
    return {"tasks": tasks}