import logging
import os
import re
import subprocess
import tempfile
import time
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from config import BASE_DIR, DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY_SECONDS
from core.powershell_mode import run_powershell

TaskResult = Dict[str, Any]
_OCR_AVAILABLE_CACHE: Optional[bool] = None


def _ok(message: str, data: Optional[Dict[str, Any]] = None) -> TaskResult:
    return {"ok": True, "message": message, "data": data or {}}


def _err(message: str, error: Optional[str] = None) -> TaskResult:
    payload: TaskResult = {"ok": False, "message": message}
    if error:
        payload["error"] = error
    return payload


def validate_path(path: str) -> str:
    """Resolve a path safely under project BASE_DIR."""
    requested = Path(path or ".")
    full_path = (Path(BASE_DIR) / requested).resolve()
    base_path = Path(BASE_DIR).resolve()
    if os.path.commonpath([str(base_path), str(full_path)]) != str(base_path):
        raise ValueError("Path outside allowed project directory")
    return str(full_path)


def _sanitize_process_name(name: str) -> str:
    cleaned = "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_", ".")).strip()
    if not cleaned:
        raise ValueError("Invalid process name")
    return cleaned


def _with_retries(label: str, operation: Callable[[], TaskResult], retries: int = DEFAULT_RETRY_COUNT) -> TaskResult:
    for attempt in range(retries + 1):
        result = operation()
        if result["ok"]:
            if attempt > 0:
                result["data"]["attempt"] = attempt + 1
            return result
        logging.warning("%s attempt %s failed: %s", label, attempt + 1, result.get("message"))
        time.sleep(DEFAULT_RETRY_DELAY_SECONDS)
    return _err(f"{label} failed after {retries + 1} attempts")


def click_at(x: int, y: int) -> TaskResult:
    try:
        import pyautogui

        pyautogui.click(x, y)
        return _ok(f"Clicked at ({x}, {y})")
    except Exception as exc:
        logging.error("Failed click_at(%s, %s): %s", x, y, exc)
        return _err(f"Could not click at ({x}, {y})", str(exc))


def click_on_text(text: str) -> TaskResult:
    if not _ocr_available():
        return _err("OCR is not available. Install Tesseract to use click-on-text.")
    try:
        import pyautogui
        import pytesseract

        screenshot = pyautogui.screenshot()
        data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
        for i, token in enumerate(data["text"]):
            if text.lower() in token.lower():
                x = data["left"][i] + data["width"][i] // 2
                y = data["top"][i] + data["height"][i] // 2
                pyautogui.click(x, y)
                return _ok(f"Clicked on '{text}'", {"x": x, "y": y})
        return _err(f"Text '{text}' not found on screen")
    except Exception as exc:
        logging.error("Failed click_on_text(%s): %s", text, exc)
        return _err(f"Could not click on '{text}'", str(exc))


def type_text(text: str) -> TaskResult:
    try:
        import pyautogui

        pyautogui.typewrite(text)
        return _ok(f"Typed '{text}'")
    except Exception as exc:
        logging.error("Failed type_text: %s", exc)
        return _err(f"Could not type '{text}'", str(exc))


def press_key(key: str) -> TaskResult:
    try:
        import pyautogui

        pyautogui.press(key)
        return _ok(f"Pressed {key}")
    except Exception as exc:
        logging.error("Failed press_key(%s): %s", key, exc)
        return _err(f"Could not press {key}", str(exc))


def hotkey(keys: List[str]) -> TaskResult:
    try:
        import pyautogui

        pyautogui.hotkey(*keys)
        return _ok(f"Pressed hotkey {'+'.join(keys)}")
    except Exception as exc:
        logging.error("Failed hotkey(%s): %s", keys, exc)
        return _err("Could not press hotkey", str(exc))


def take_screenshot() -> TaskResult:
    try:
        import pyautogui

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=BASE_DIR) as tmp:
            path = tmp.name
        image = pyautogui.screenshot()
        image.save(path)
        return _ok("Screenshot saved", {"path": path})
    except Exception as exc:
        logging.error("take_screenshot failed: %s", exc)
        return _err("Failed to take screenshot", str(exc))


def youtube_search(query: str) -> TaskResult:
    """Search YouTube: focus address bar, set search URL, press enter."""
    try:
        import pyautogui
        import time as time_module

        # Focus address bar (Chrome/Edge/Firefox - Ctrl+L is universal)
        pyautogui.hotkey("ctrl", "l")
        time_module.sleep(0.2)
        
        # Properly encode the search query
        encoded_query = urllib.parse.quote_plus(query.strip())
        url = f"https://www.youtube.com/results?search_query={encoded_query}"

        try:
            import pyperclip

            pyperclip.copy(url)
            pyautogui.hotkey("ctrl", "v")
        except Exception:
            pyautogui.typewrite(url, interval=0.01)
        
        time_module.sleep(0.1)
        pyautogui.press("enter")
        time_module.sleep(0.5)
        return _ok(f"Searched YouTube for: {query}")
    except Exception as exc:
        logging.error("youtube_search failed: %s", exc)
        return _err("Failed to search YouTube", str(exc))


def play_in_youtube(query: str) -> TaskResult:
    """Open first YouTube video result for query."""
    try:
        from youtubesearchpython import VideosSearch

        term = query.strip()
        if not term:
            return _err("Please provide something to play on YouTube.")
        videos = VideosSearch(term, limit=1)
        items = videos.result().get("result", [])
        if not items:
            return _err(f"No YouTube results found for: {term}")
        url = items[0].get("link")
        if not isinstance(url, str) or not url:
            return _err("Failed to get YouTube result URL")
        webbrowser.open(url)
        return _ok(f"Playing on YouTube: {term}", {"url": url})
    except Exception as exc:
        logging.error("play_in_youtube failed: %s", exc)
        return _err("Failed to play on YouTube", str(exc))


def get_current_time() -> TaskResult:
    """Speak/read current local time."""
    now_str = datetime.now().strftime("%H:%M:%S")
    return _ok(f"The current time is {now_str}", {"time": now_str})


def wikipedia_summary(query: str) -> TaskResult:
    """Fetch a concise Wikipedia summary."""
    try:
        import wikipedia

        term = query.strip()
        if not term:
            return _err("Please provide a topic for Wikipedia.")
        summary = wikipedia.summary(term, sentences=2)
        return _ok(summary, {"topic": term, "summary": summary})
    except Exception as exc:
        logging.error("wikipedia_summary failed: %s", exc)
        return _err("Failed to fetch Wikipedia summary", str(exc))


def google_search(query: str) -> TaskResult:
    """Search Google: navigate to Google search."""
    try:
        encoded_query = query.strip().replace(" ", "+")
        url = f"https://www.google.com/search?q={encoded_query}"
        webbrowser.open(url)
        return _ok(f"Searched Google for: {query}")
    except Exception as exc:
        logging.error("google_search failed: %s", exc)
        return _err("Failed to search Google", str(exc))


def wikipedia_search(query: str) -> TaskResult:
    """Search Wikipedia."""
    try:
        encoded_query = query.strip().replace(" ", "_")
        url = f"https://en.wikipedia.org/wiki/{encoded_query}"
        webbrowser.open(url)
        return _ok(f"Searched Wikipedia for: {query}")
    except Exception as exc:
        logging.error("wikipedia_search failed: %s", exc)
        return _err("Failed to search Wikipedia", str(exc))


def amazon_search(query: str) -> TaskResult:
    """Search Amazon India for products."""
    try:
        encoded_query = query.strip().replace(" ", "+")
        url = f"https://www.amazon.in/s?k={encoded_query}"
        webbrowser.open(url)
        return _ok(f"Searched Amazon for: {query}")
    except Exception as exc:
        logging.error("amazon_search failed: %s", exc)
        return _err("Failed to search Amazon", str(exc))


def hotstar_search(query: str) -> TaskResult:
    """Search Hotstar for movies/shows."""
    try:
        encoded_query = query.strip().replace(" ", "+")
        url = f"https://www.hotstar.com/in/explore?search_query={encoded_query}"
        webbrowser.open(url)
        return _ok(f"Searched Hotstar for: {query}")
    except Exception as exc:
        logging.error("hotstar_search failed: %s", exc)
        return _err("Failed to search Hotstar", str(exc))


def spotify_search(query: str) -> TaskResult:
    """Search Spotify for music."""
    try:
        encoded_query = query.strip().replace(" ", "%20")
        url = f"https://open.spotify.com/search/{encoded_query}"
        webbrowser.open(url)
        return _ok(f"Searched Spotify for: {query}")
    except Exception as exc:
        logging.error("spotify_search failed: %s", exc)
        return _err("Failed to search Spotify", str(exc))


def linkedin_search(query: str) -> TaskResult:
    """Search LinkedIn."""
    try:
        encoded_query = query.strip().replace(" ", "%20")
        url = f"https://www.linkedin.com/search/results/all/?keywords={encoded_query}"
        webbrowser.open(url)
        return _ok(f"Searched LinkedIn for: {query}")
    except Exception as exc:
        logging.error("linkedin_search failed: %s", exc)
        return _err("Failed to search LinkedIn", str(exc))


def github_search(query: str) -> TaskResult:
    """Search GitHub for code/repositories."""
    try:
        encoded_query = query.strip().replace(" ", "+")
        url = f"https://github.com/search?q={encoded_query}"
        webbrowser.open(url)
        return _ok(f"Searched GitHub for: {query}")
    except Exception as exc:
        logging.error("github_search failed: %s", exc)
        return _err("Failed to search GitHub", str(exc))


def twitter_search(query: str) -> TaskResult:
    """Search Twitter/X."""
    try:
        encoded_query = query.strip().replace(" ", "%20")
        url = f"https://twitter.com/search?q={encoded_query}"
        webbrowser.open(url)
        return _ok(f"Searched Twitter for: {query}")
    except Exception as exc:
        logging.error("twitter_search failed: %s", exc)
        return _err("Failed to search Twitter", str(exc))


def google_news_search(query: str) -> TaskResult:
    """Search Google News."""
    try:
        encoded_query = query.strip().replace(" ", "+")
        url = f"https://news.google.com/search?q={encoded_query}"
        webbrowser.open(url)
        return _ok(f"Searched Google News for: {query}")
    except Exception as exc:
        logging.error("google_news_search failed: %s", exc)
        return _err("Failed to search Google News", str(exc))


def maps_search(query: str) -> TaskResult:
    """Search Google Maps for locations."""
    try:
        encoded_query = query.strip().replace(" ", "+")
        url = f"https://www.google.com/maps/search/{encoded_query}"
        webbrowser.open(url)
        return _ok(f"Searched Google Maps for: {query}")
    except Exception as exc:
        logging.error("maps_search failed: %s", exc)
        return _err("Failed to search Google Maps", str(exc))


def pypi_search(query: str) -> TaskResult:
    """Search PyPI for Python packages."""
    try:
        encoded_query = query.strip().replace(" ", "+")
        url = f"https://pypi.org/search/?q={encoded_query}"
        webbrowser.open(url)
        return _ok(f"Searched PyPI for: {query}")
    except Exception as exc:
        logging.error("pypi_search failed: %s", exc)
        return _err("Failed to search PyPI", str(exc))


def gaana_search(query: str) -> TaskResult:
    """Search Gaana for music."""
    try:
        encoded_query = query.strip().replace(" ", "%20")
        url = f"https://gaana.com/search/{encoded_query}"
        webbrowser.open(url)
        return _ok(f"Searched Gaana for: {query}")
    except Exception as exc:
        logging.error("gaana_search failed: %s", exc)
        return _err("Failed to search Gaana", str(exc))


def open_app(app_name: str) -> TaskResult:
    try:
        safe_name = _sanitize_process_name(app_name)
        if os.name == "nt":
            # Try direct startfile first (handles shortcuts, documents, etc.)
            try:
                os.startfile(safe_name)  # type: ignore[attr-defined]
                return _ok(f"Opened {app_name}")
            except Exception:
                # Try with .exe extension if it failed
                try:
                    exe_name = safe_name if safe_name.endswith(".exe") else f"{safe_name}.exe"
                    subprocess.run([exe_name], check=False, capture_output=True)
                    return _ok(f"Opened {app_name}")
                except Exception as inner_exc:
                    logging.debug("open_app subprocess failed: %s", inner_exc)
                    return _err(f"Could not open {app_name}", str(inner_exc))
        else:
            subprocess.run([safe_name], check=False, capture_output=True)
            return _ok(f"Opened {app_name}")
    except Exception as exc:
        logging.error("Failed open_app(%s): %s", app_name, exc)
        return _err(f"Could not open {app_name}", str(exc))


def close_app(app_name: str) -> TaskResult:
    try:
        safe_name = _sanitize_process_name(app_name)
        if os.name == "nt":
            process_name = safe_name if safe_name.endswith(".exe") else f"{safe_name}.exe"
            result = subprocess.run(
                ["taskkill", "/f", "/im", process_name],
                capture_output=True,
                text=True
            )
            # Exit code 0 = success, 1 = no process found (still acceptable)
            if result.returncode not in (0, 1):
                logging.warning("taskkill returned code %d for %s", result.returncode, app_name)
        else:
            result = subprocess.run(
                ["pkill", "-f", safe_name],
                capture_output=True,
                text=True
            )
            # Exit code 0 = success, 1 = no process found (still acceptable)
            if result.returncode not in (0, 1):
                logging.warning("pkill returned code %d for %s", result.returncode, app_name)
        return _ok(f"Closed {app_name}")
    except Exception as exc:
        logging.error("Failed close_app(%s): %s", app_name, exc)
        return _err(f"Could not close {app_name}", str(exc))


def ocr_screen(region: Optional[tuple] = None) -> str:
    try:
        import pyautogui
        import pytesseract

        screenshot = pyautogui.screenshot(region=region)
        return pytesseract.image_to_string(screenshot).lower()
    except Exception as exc:
        logging.error("OCR failed: %s", exc)
        return ""


def _ocr_available() -> bool:
    global _OCR_AVAILABLE_CACHE
    if _OCR_AVAILABLE_CACHE is not None:
        return _OCR_AVAILABLE_CACHE
    try:
        import pytesseract

        _ = pytesseract.get_tesseract_version()
        _OCR_AVAILABLE_CACHE = True
        return True
    except Exception:
        _OCR_AVAILABLE_CACHE = False
        return False


def summarize_screen() -> TaskResult:
    if not _ocr_available():
        return _err("OCR is not available. Install Tesseract to use screen reading features.")
    text = ocr_screen()
    if not text.strip():
        return _err("Could not read enough text from the screen")
    try:
        from brain.llm import get_response

        prompt = f"Summarize this screen content in 4 concise bullet points:\n{text[:3000]}"
        summary = get_response(prompt)
        if summary.get("task") == "chat":
            return _ok("Screen summary ready", {"summary": summary.get("parameters", {}).get("message", "")})
        return _ok("Screen summary ready", {"summary": str(summary)})
    except Exception as exc:
        logging.error("summarize_screen failed: %s", exc)
        return _err("Failed to summarize screen", str(exc))


def extract_emails_from_screen() -> TaskResult:
    if not _ocr_available():
        return _err("OCR is not available. Install Tesseract to use screen reading features.")
    text = ocr_screen()
    if not text.strip():
        return _err("Could not read enough text from the screen")
    emails = sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))
    return _ok(f"Found {len(emails)} email(s)", {"emails": emails})


def autofill_form(profile: Optional[Dict[str, str]] = None) -> TaskResult:
    if not _ocr_available():
        return _err("OCR is not available. Install Tesseract to use autofill.")
    profile_data = profile or {
        "name": os.getenv("KARN_PROFILE_NAME", os.getenv("MENU_PROFILE_NAME", "")),
        "email": os.getenv("KARN_PROFILE_EMAIL", os.getenv("MENU_PROFILE_EMAIL", "")),
        "phone": os.getenv("KARN_PROFILE_PHONE", os.getenv("MENU_PROFILE_PHONE", "")),
    }
    try:
        import pyautogui
        import pytesseract

        screenshot = pyautogui.screenshot()
        data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
        typed_fields: List[str] = []

        for i, token in enumerate(data["text"]):
            label = token.strip().lower()
            value = ""
            if "name" in label and profile_data.get("name"):
                value = profile_data["name"]
            elif "email" in label and profile_data.get("email"):
                value = profile_data["email"]
            elif "phone" in label and profile_data.get("phone"):
                value = profile_data["phone"]

            if value:
                x = data["left"][i] + data["width"][i] + 120
                y = data["top"][i] + data["height"][i] // 2
                pyautogui.click(x, y)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.typewrite(value, interval=0.03)
                typed_fields.append(label)
                time.sleep(0.1)

        if not typed_fields:
            return _err("No supported fields found for autofill (name/email/phone)")
        return _ok("Autofill completed", {"fields": typed_fields})
    except Exception as exc:
        logging.error("autofill_form failed: %s", exc)
        return _err("Failed to autofill form", str(exc))


def open_whatsapp() -> TaskResult:
    def _op() -> TaskResult:
        webbrowser.open("https://web.whatsapp.com")
        time.sleep(4)
        if not _ocr_available():
            return _ok("Opened WhatsApp Web (OCR not available to verify)")
        text = ocr_screen()
        if "whatsapp" in text or "chat" in text:
            return _ok("Opened WhatsApp Web")
        return _err("WhatsApp Web may not have loaded properly")

    return _with_retries("open_whatsapp", _op, retries=1)


def send_whatsapp_message(contact: str, message: str) -> TaskResult:
    def _op() -> TaskResult:
        import pyautogui

        windows = pyautogui.getAllWindows()
        whatsapp_win = next((win for win in windows if "whatsapp" in win.title.lower()), None)
        if not whatsapp_win:
            return _err("WhatsApp window not found. Please open WhatsApp Web manually.")

        whatsapp_win.activate()
        time.sleep(1)
        pyautogui.hotkey("ctrl", "/")
        time.sleep(1)
        pyautogui.typewrite(contact, interval=0.1)
        time.sleep(2)
        if _ocr_available() and contact.lower() not in ocr_screen():
            return _err(f"Contact '{contact}' not found yet")

        pyautogui.press("enter")
        time.sleep(1)
        pyautogui.typewrite(message, interval=0.05)
        time.sleep(1)
        pyautogui.press("enter")
        time.sleep(1)
        return _ok(f"Sent message to {contact}")

    return _with_retries("send_whatsapp_message", _op, retries=2)


def open_url(url: str) -> TaskResult:
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return _ok(f"Opened {url}")
    except Exception as exc:
        logging.error("open_url failed: %s", exc)
        return _err("Failed to open URL", str(exc))


def execute_task(task: str, parameters: Optional[Dict[str, Any]] = None) -> TaskResult:
    params = parameters or {}
    try:
        if task == "create_folder":
            path = validate_path(params.get("path", ""))
            name = params["name"]
            full_path = Path(path) / name
            full_path.mkdir(parents=True, exist_ok=True)
            return _ok(f"Created folder {name}")

        if task == "delete_folder":
            path = Path(validate_path(params["path"]))
            if not path.exists():
                return _err("Folder not found")
            path.rmdir()
            return _ok(f"Deleted folder {params['path']}")

        if task == "create_file":
            path = validate_path(params.get("path", ""))
            name = params["name"]
            content = params.get("content", "")
            full_path = Path(path) / name
            full_path.write_text(content, encoding="utf-8")
            return _ok(f"Created file {name}")

        if task == "open_file":
            target = Path(validate_path(params["path"]))
            if not target.exists():
                return _err("File not found")
            os.startfile(str(target))  # type: ignore[attr-defined]
            return _ok(f"Opened file {target.name}")

        if task == "read_file":
            target = Path(validate_path(params["path"]))
            content = target.read_text(encoding="utf-8")
            return _ok(f"Content: {content[:200]}...")

        if task == "write_file":
            target = Path(validate_path(params["path"]))
            target.write_text(params["content"], encoding="utf-8")
            return _ok(f"Wrote to {params['path']}")

        if task == "append_file":
            target = Path(validate_path(params["path"]))
            with target.open("a", encoding="utf-8") as handle:
                handle.write(params["content"])
            return _ok(f"Appended to {params['path']}")

        if task == "delete_file":
            target = Path(validate_path(params["path"]))
            if not target.exists():
                return _err("File not found")
            target.unlink()
            return _ok(f"Deleted file {params['path']}")

        if task == "list_files":
            path = Path(validate_path(params.get("path", "")))
            return _ok("Listed files", {"items": os.listdir(path)})

        if task == "search_file":
            name = params["name"]
            results: List[str] = []
            for root, _dirs, files in os.walk(BASE_DIR):
                if name in files:
                    results.append(os.path.relpath(os.path.join(root, name), BASE_DIR))
            return _ok(f"Found files: {results}", {"results": results})

        if task == "open_app":
            return open_app(params["name"])

        if task == "open_url":
            return open_url(params["url"])

        if task == "run_powershell":
            # This is guarded by config + confirmation flow in AssistantService.
            result = run_powershell(params["command"])
            if result.get("ok") == "true":
                return _ok(result.get("message", "PowerShell command completed."), {"stdout": result.get("stdout", "")})
            return _err(result.get("message", "PowerShell command failed."), result.get("stderr"))

        if task == "close_app":
            return close_app(params["name"])

        if task == "open_folder":
            path = validate_path(params["path"])
            os.startfile(path)  # type: ignore[attr-defined]
            return _ok(f"Opened folder {params['path']}")

        if task == "type_text":
            return type_text(params["text"])

        if task == "press_key":
            return press_key(params["key"])

        if task == "hotkey":
            return hotkey(params["keys"])

        if task == "click_on_text":
            return click_on_text(params["text"])

        if task == "click_at":
            return click_at(int(params["x"]), int(params["y"]))

        if task == "open_whatsapp":
            return open_whatsapp()

        if task == "send_whatsapp_message":
            return send_whatsapp_message(params["contact"], params["message"])

        if task == "check_emails":
            webbrowser.open("https://mail.google.com")
            return _ok("Opened Gmail")

        if task == "read_screen":
            text = ocr_screen()
            return _ok(f"Screen text: {text[:500]}...")

        if task == "summarize_screen":
            summary_result = summarize_screen()
            if summary_result["ok"]:
                return _ok(summary_result["data"].get("summary", "Summary complete."))
            return summary_result

        if task == "extract_emails_from_screen":
            result = extract_emails_from_screen()
            if result["ok"]:
                emails = result["data"].get("emails", [])
                return _ok(f"Emails: {emails}")
            return result

        if task == "autofill_form":
            return autofill_form(params.get("profile"))

        if task == "take_screenshot":
            result = take_screenshot()
            if result["ok"]:
                return _ok(f"Screenshot saved to {result['data'].get('path')}")
            return result

        if task == "youtube_search":
            return youtube_search(params["query"])

        if task == "play_in_youtube":
            return play_in_youtube(params["query"])

        if task == "google_search":
            return google_search(params["query"])

        if task == "wikipedia_search":
            return wikipedia_search(params["query"])

        if task == "wikipedia_summary":
            return wikipedia_summary(params["query"])

        if task == "amazon_search":
            return amazon_search(params["query"])

        if task == "hotstar_search":
            return hotstar_search(params["query"])

        if task == "spotify_search":
            return spotify_search(params["query"])

        if task == "linkedin_search":
            return linkedin_search(params["query"])

        if task == "github_search":
            return github_search(params["query"])

        if task == "twitter_search":
            return twitter_search(params["query"])

        if task == "google_news_search":
            return google_news_search(params["query"])

        if task == "maps_search":
            return maps_search(params["query"])

        if task == "pypi_search":
            return pypi_search(params["query"])

        if task == "gaana_search":
            return gaana_search(params["query"])

        if task == "get_current_time":
            return get_current_time()

        if task == "greet":
            return _ok("Hello! How can I help you?")

        return _err(f"Unknown task: {task}")
    except KeyError as exc:
        logging.error("Missing parameter for %s: %s", task, exc)
        return _err(f"Missing parameter: {exc}")
    except Exception as exc:
        logging.error("Error executing %s with %s: %s", task, params, exc)
        return _err(f"Error executing {task}", str(exc))