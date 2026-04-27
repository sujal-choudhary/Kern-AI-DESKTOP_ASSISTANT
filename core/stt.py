#!/usr/bin/env python3
"""Offline STT pipeline: Mic -> Stream -> VAD -> Buffer -> Chunk -> Whisper -> Text."""

import logging
import queue
import threading
import time
from typing import Optional

import numpy as np
import sounddevice as sd

try:
    import whisper
except Exception:  # pragma: no cover
    whisper = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_RUNNING = False
_MODEL = None

_SAMPLE_RATE = 16000
_CHANNELS = 1
_BLOCK_SECONDS = 0.1
_CHUNK_SECONDS = 2.0
_BLOCK_SIZE = int(_SAMPLE_RATE * _BLOCK_SECONDS)
_CHUNK_SIZE = int(_SAMPLE_RATE * _CHUNK_SECONDS)

_STREAM_QUEUE: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=400)
_VAD_QUEUE: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=300)
_CHUNK_QUEUE: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=80)
_RESULT_QUEUE: "queue.Queue[str]" = queue.Queue(maxsize=50)

_CAPTURE_THREAD: Optional[threading.Thread] = None
_VAD_THREAD: Optional[threading.Thread] = None
_CHUNK_THREAD: Optional[threading.Thread] = None
_PROCESS_THREAD: Optional[threading.Thread] = None

_LAST_PARTIAL = ""
_TRANSCRIPT = ""
_VAD_ENERGY_THRESHOLD = 0.00025


def _load_model() -> bool:
    global _MODEL
    if _MODEL is not None:
        return True
    if whisper is None:
        logger.error("Whisper is not installed. Install package 'openai-whisper'.")
        return False
    try:
        _MODEL = whisper.load_model("base")
        return True
    except Exception as exc:
        logger.error("Failed to load Whisper model: %s", exc)
        return False


def _audio_callback(indata, frames, time_info, status) -> None:
    if status:
        logger.debug("Audio callback status: %s", status)
    with _LOCK:
        running = _RUNNING
    if not running:
        return
    try:
        _STREAM_QUEUE.put_nowait(indata[:, 0].copy().astype(np.float32))
    except queue.Full:
        logger.debug("Stream queue full; dropping audio block")


def _capture_loop() -> None:
    try:
        with sd.InputStream(
            samplerate=_SAMPLE_RATE,
            channels=_CHANNELS,
            dtype="float32",
            blocksize=_BLOCK_SIZE,
            callback=_audio_callback,
        ):
            while True:
                with _LOCK:
                    if not _RUNNING:
                        break
                time.sleep(0.05)
    except Exception as exc:
        logger.error("Microphone stream failed: %s", exc)


def _vad_loop() -> None:
    """Simple energy-based VAD gate between stream and chunking."""
    global _LAST_PARTIAL
    while True:
        with _LOCK:
            running = _RUNNING
        if not running and _STREAM_QUEUE.empty():
            break
        try:
            block = _STREAM_QUEUE.get(timeout=0.2)
        except queue.Empty:
            continue

        energy = float(np.mean(block * block))
        if energy >= _VAD_ENERGY_THRESHOLD:
            try:
                _VAD_QUEUE.put(block, timeout=0.2)
                _LAST_PARTIAL = "voice detected..."
            except queue.Full:
                logger.debug("VAD queue full; dropping voiced block")
        else:
            _LAST_PARTIAL = "silence"


def _chunk_loop() -> None:
    global _LAST_PARTIAL
    buffer = np.array([], dtype=np.float32)
    while True:
        with _LOCK:
            running = _RUNNING
        if not running and _VAD_QUEUE.empty():
            break
        try:
            block = _VAD_QUEUE.get(timeout=0.2)
        except queue.Empty:
            continue
        buffer = np.concatenate((buffer, block))
        _LAST_PARTIAL = "buffering audio..."
        while buffer.size >= _CHUNK_SIZE:
            chunk = buffer[:_CHUNK_SIZE]
            buffer = buffer[_CHUNK_SIZE:]
            try:
                _CHUNK_QUEUE.put(chunk, timeout=0.2)
            except queue.Full:
                logger.debug("Chunk queue full; dropping chunk")
    if buffer.size > int(_SAMPLE_RATE * 0.6):
        try:
            _CHUNK_QUEUE.put(buffer, timeout=0.2)
        except queue.Full:
            pass


def _process_loop() -> None:
    global _LAST_PARTIAL, _TRANSCRIPT
    while True:
        with _LOCK:
            running = _RUNNING
        if not running and _CHUNK_QUEUE.empty():
            break
        try:
            chunk = _CHUNK_QUEUE.get(timeout=0.2)
        except queue.Empty:
            continue
        try:
            _LAST_PARTIAL = "processing chunk..."
            result = _MODEL.transcribe(chunk, language="en", fp16=False, verbose=False) if _MODEL is not None else {}
            text = str(result.get("text", "")).strip()
            if text:
                with _LOCK:
                    _TRANSCRIPT = f"{_TRANSCRIPT} {text}".strip()
                try:
                    _RESULT_QUEUE.put(text, timeout=0.2)
                except queue.Full:
                    pass
                _LAST_PARTIAL = text
            else:
                _LAST_PARTIAL = ""
        except Exception as exc:
            logger.error("Whisper processing failed: %s", exc)
            _LAST_PARTIAL = ""


def start_offline_stt() -> bool:
    global _RUNNING, _CAPTURE_THREAD, _VAD_THREAD, _CHUNK_THREAD, _PROCESS_THREAD
    with _LOCK:
        if _RUNNING:
            return True
    if not _load_model():
        return False
    with _LOCK:
        _RUNNING = True
    _CAPTURE_THREAD = threading.Thread(target=_capture_loop, daemon=True, name="stt-capture")
    _VAD_THREAD = threading.Thread(target=_vad_loop, daemon=True, name="stt-vad")
    _CHUNK_THREAD = threading.Thread(target=_chunk_loop, daemon=True, name="stt-chunker")
    _PROCESS_THREAD = threading.Thread(target=_process_loop, daemon=True, name="stt-whisper")
    _CAPTURE_THREAD.start()
    _VAD_THREAD.start()
    _CHUNK_THREAD.start()
    _PROCESS_THREAD.start()
    logger.info("Offline STT pipeline started (Mic -> Stream -> VAD -> Buffer -> Chunk -> Whisper)")
    return True


def stop_offline_stt() -> None:
    global _RUNNING
    with _LOCK:
        _RUNNING = False
    for thread in (_CAPTURE_THREAD, _VAD_THREAD, _CHUNK_THREAD, _PROCESS_THREAD):
        if thread and thread.is_alive():
            thread.join(timeout=1.5)
    logger.info("Offline STT pipeline stopped")


def listen() -> Optional[str]:
    try:
        return _RESULT_QUEUE.get(timeout=0.8)
    except queue.Empty:
        return None


def get_current_transcript() -> str:
    with _LOCK:
        return _TRANSCRIPT


def clear_transcript() -> None:
    global _LAST_PARTIAL, _TRANSCRIPT
    with _LOCK:
        _LAST_PARTIAL = ""
        _TRANSCRIPT = ""
    while not _RESULT_QUEUE.empty():
        try:
            _RESULT_QUEUE.get_nowait()
        except queue.Empty:
            break


def get_live_state() -> dict[str, object]:
    with _LOCK:
        return {
            "running": _RUNNING,
            "partial": _LAST_PARTIAL,
            "transcript": _TRANSCRIPT,
            "stream_queue": _STREAM_QUEUE.qsize(),
            "vad_queue": _VAD_QUEUE.qsize(),
            "chunk_queue": _CHUNK_QUEUE.qsize(),
        }