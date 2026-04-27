import logging
import os
from pathlib import Path

# Core runtime settings (prefer KARN_*; keep MENU_* for compatibility)
MODEL = os.getenv("KARN_MODEL", os.getenv("MENU_MODEL", "gemma3:1b"))
VOICE_MODEL_PATH = os.getenv("KARN_VOICE_MODEL_PATH", os.getenv("MENU_VOICE_MODEL_PATH", "en_US-lessac-medium.onnx"))
DEFAULT_RETRY_COUNT = int(os.getenv("KARN_DEFAULT_RETRY_COUNT", os.getenv("MENU_DEFAULT_RETRY_COUNT", "2")))
DEFAULT_RETRY_DELAY_SECONDS = float(
    os.getenv("KARN_DEFAULT_RETRY_DELAY_SECONDS", os.getenv("MENU_DEFAULT_RETRY_DELAY_SECONDS", "1.0"))
)
STT_AMBIENT_CALIBRATION_SECONDS = float(
    os.getenv("KARN_STT_AMBIENT_CALIBRATION_SECONDS", os.getenv("MENU_STT_AMBIENT_CALIBRATION_SECONDS", "0.25"))
)
STT_RECALIBRATE_INTERVAL_SECONDS = float(
    os.getenv("KARN_STT_RECALIBRATE_INTERVAL_SECONDS", os.getenv("MENU_STT_RECALIBRATE_INTERVAL_SECONDS", "90"))
)
LLM_HISTORY_TURNS = int(os.getenv("KARN_LLM_HISTORY_TURNS", os.getenv("MENU_LLM_HISTORY_TURNS", "3")))
LLM_NUM_CTX = int(os.getenv("KARN_LLM_NUM_CTX", os.getenv("MENU_LLM_NUM_CTX", "1024")))

# Project boundaries (repo-level access requested)
BASE_DIR = str(Path(__file__).resolve().parent.parent)
MEMORY_STORE_PATH = os.getenv("KARN_MEMORY_STORE_PATH", os.getenv("MENU_MEMORY_STORE_PATH", str(Path(BASE_DIR) / "memory_store.json")))
WEB_HOST = os.getenv("KARN_WEB_HOST", os.getenv("MENU_WEB_HOST", "127.0.0.1"))
WEB_PORT = int(os.getenv("KARN_WEB_PORT", os.getenv("MENU_WEB_PORT", "5000")))
AUTO_START_WEB_PANEL = os.getenv("KARN_AUTO_START_WEB_PANEL", os.getenv("MENU_AUTO_START_WEB_PANEL", "true")).lower() in (
    "1",
    "true",
    "yes",
)

# PowerShell (Confirm mode)
ENABLE_POWERSHELL = os.getenv("KARN_ENABLE_POWERSHELL", os.getenv("MENU_ENABLE_POWERSHELL", "false")).lower() in (
    "1",
    "true",
    "yes",
)
POWERSHELL_CONFIRM_PASSPHRASE = os.getenv("KARN_POWERSHELL_PASSPHRASE", os.getenv("MENU_POWERSHELL_PASSPHRASE", ""))
POWERSHELL_TIMEOUT_SECONDS = int(os.getenv("KARN_POWERSHELL_TIMEOUT_SECONDS", os.getenv("MENU_POWERSHELL_TIMEOUT_SECONDS", "20")))

# Logging setup
logging.basicConfig(
    filename="karn.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)