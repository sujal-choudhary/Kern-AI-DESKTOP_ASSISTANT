# Karn AI Desktop Assistant

Karn AI is a local-first desktop automation assistant with voice input, text command fallback, and a web control panel.  
It combines deterministic command parsing with LLM fallback (Ollama) so common commands are fast and predictable while open-ended prompts still work.

## Features

- Offline speech-to-text pipeline (Vosk + Whisper + VAD) for live and final transcripts.
- Voice and text command handling with safe task execution.
- Desktop automation actions (open/close apps, type text, click at coordinates, screenshots).
- Browser and web automation helpers (Google, YouTube, Wikipedia, GitHub, Maps, and more).
- WhatsApp automation (`open_whatsapp`, `send_whatsapp_message`).
- OCR-powered features (`click_on_text`, screen summarization, email extraction, autofill form).
- Memory and learned command mappings (`when i say ..., ...`) persisted across sessions.
- PowerShell confirm flow for safer shell execution.
- Built-in Flask web panel to monitor status, send commands, and control voice mode.

## How It Works

- `core/commands.py`: fast deterministic parser for common phrases.
- `brain/llm.py`: LLM response normalization and fallback orchestration.
- `core/actions.py`: executable task handlers with structured result format.
- `core/assistant_service.py`: central runtime service (voice loop, memory, command routing).
- `web_panel.py`: local control panel and API endpoints.

## Requirements

- Python 3.10+ recommended
- Ollama installed and running
- Microphone + speaker access
- Extra RAM/storage for offline STT models
- Optional: Tesseract OCR for screen-text features

## Quick Start

```bash
pip install -r requirements.txt
python setup_offline_stt.py
python main.py
```

If needed, pull your default Ollama model first:

```bash
ollama pull llama2
```

## Usage

- Start assistant: `python main.py`
- Start only web panel: `python web_panel.py`
- Web UI URL: `http://127.0.0.1:5000` (default)

### Example Commands

- `open notepad`
- `open youtube and then search lofi hip hop on youtube`
- `create folder test`
- `fill this form`
- `extract all emails from this screen`
- `when i say clean desktop, delete folder temp`

## Configuration

Set these environment variables as needed:

- `KARN_MODEL` (default: `llama2`)
- `KARN_VOICE_MODEL_PATH` (default: `en_US-lessac-medium.onnx`)
- `KARN_DEFAULT_RETRY_COUNT` (default: `2`)
- `KARN_DEFAULT_RETRY_DELAY_SECONDS` (default: `1.0`)
- `KARN_MEMORY_STORE_PATH` (default: `memory_store.json`)
- `KARN_WEB_HOST` (default: `127.0.0.1`)
- `KARN_WEB_PORT` (default: `5000`)
- `KARN_AUTO_START_WEB_PANEL` (default: `true`)
- `KARN_PROFILE_NAME`, `KARN_PROFILE_EMAIL`, `KARN_PROFILE_PHONE` (for autofill)
- Legacy `MENU_*` variables are still supported for backward compatibility.

## Testing

```bash
pytest -q
```

Current baseline: tests pass locally.

## Troubleshooting

- **STT not starting:** rerun `python setup_offline_stt.py` and verify model paths.
- **No OCR features:** install Tesseract and ensure it is available in PATH.
- **LLM issues:** confirm Ollama daemon is running and model exists.
- **Voice output issues:** verify Piper model file and audio device permissions.

## Security Notes

- PowerShell commands run through a confirmation gate.
- Filesystem operations are validated against the project base directory.
- OCR/automation actions may need explicit OS accessibility permissions.

## Project Status

This project is actively evolving toward reliable local automation and safer execution defaults. Contributions and issue reports are welcome.