# Offline Speech-to-Text Setup Guide

This guide will help you set up the **fully offline real-time Speech-to-Text (STT) system** for the Menu AI Assistant.

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run setup script (downloads models automatically)
python setup_offline_stt.py

# 3. Start the assistant
python main.py
```

## 📋 System Requirements

- **Python**: 3.8 or higher
- **RAM**: Minimum 2GB (4GB recommended)
- **Storage**: ~40MB for Vosk model
- **Microphone**: Any working microphone
- **OS**: Windows, Linux, or macOS

## 🔧 Detailed Setup

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `sounddevice` - Audio capture
- `numpy` - Audio processing
- `torch` - Machine learning framework
- `vosk` - Fast and accurate STT
- `silero-vad` - Voice activity detection

### Step 2: Download Models

Run the setup script:

```bash
python setup_offline_stt.py
```

This script will:
- ✅ Download Vosk English model (~40MB)
- ✅ Verify Whisper model download
- ✅ Test all components
- ✅ Report setup status

**Expected output:**
```
🚀 Setting up Offline STT System
==================================================
🐍 Python version: 3.10.0
🔧 Installing Python dependencies... ✅
📥 Downloading Vosk English model (small)... ✅
📦 Extracting model... ✅
🧪 Testing components...
✅ Whisper model loaded successfully
✅ Vosk model loaded successfully
✅ Silero VAD loaded successfully

📊 Test Results: 3/3 passed

🎉 Setup completed successfully!
```

### Step 3: Manual Model Download (Alternative)

If the automatic download fails, you can download models manually:

#### Vosk Model
```bash
# Download from: https://alphacephei.com/vosk/models/
# Choose: vosk-model-small-en-us-0.15.zip (~40MB)

# Extract to:
# models/vosk-model-small-en-us-0.15/
```

#### Whisper Model
Whisper models are downloaded automatically on first use. No manual action needed.

## 🎯 How It Works

### Architecture Overview

```
Microphone Input
       ↓
   Audio Capture (sounddevice)
       ↓
   Voice Activity Detection (Silero VAD)
       ↓
   Audio Chunking (2s chunks + 0.5s overlap)
       ↓
   ┌─────────────────┬─────────────────┐
   │   Fast Preview  │  Accurate Final │
   │     (Vosk)      │   (Whisper)     │
   │                 │                 │
   │ [LIVE] hello... │ [FINAL] hello   │
   └─────────────────┴─────────────────┘
       ↓
   Deduplication & Merging
       ↓
   Global Transcript
```

### Threading Model

- **Thread 1**: Audio capture from microphone
- **Thread 2**: VAD processing and chunking
- **Thread 3**: Vosk fast transcription (live preview)
- **Thread 4**: Whisper accurate transcription (final output)

### Real-Time Output

The system provides two types of output:

```
[LIVE] hello my na...     # Fast, real-time preview
[FINAL] hello my name is sujal  # Accurate, corrected final text
```

## 🧪 Testing the System

### Basic Test

```python
from core.stt import start_offline_stt, get_current_transcript

# Start the system
start_offline_stt()

# Speak into your microphone
# Watch for [LIVE] and [FINAL] outputs

# Get current transcript
transcript = get_current_transcript()
print(f"Full transcript: {transcript}")
```

### Integration Test

```bash
# Start the assistant
python main.py

# Say commands like:
# "open notepad"
# "search python tutorial on youtube"
# "what time is it"
```

## ⚙️ Configuration

### Audio Settings

Edit `core/stt.py`:

```python
# Audio configuration
SAMPLE_RATE = 16000      # 16kHz optimal for STT
CHANNELS = 1            # Mono audio
CHUNK_DURATION = 2.0    # 2-second processing chunks
OVERLAP_DURATION = 0.5  # 0.5-second overlap
VAD_THRESHOLD = 0.5     # Voice activity sensitivity
```

### Model Settings

```python
WHISPER_MODEL_SIZE = "tiny"  # Options: tiny, base, small, medium, large
```

### Performance Tuning

- **For speed**: Use `"tiny"` Whisper model
- **For accuracy**: Use `"base"` or `"small"` Whisper model
- **For low RAM**: Keep `"tiny"` and limit concurrent processing

## 🔧 Troubleshooting

### Common Issues

#### 1. "Offline STT dependencies not available"

**Solution**: Install dependencies
```bash
pip install sounddevice numpy torch openai-whisper vosk silero-vad
```

#### 2. "Vosk model not found"

**Solution**: Run setup script or download manually
```bash
python setup_offline_stt.py
```

#### 3. "No audio input" or "Microphone not working"

**Solution**: Check microphone permissions and test with:
```python
import sounddevice as sd
print(sd.query_devices())
```

#### 4. "CUDA out of memory" (GPU users)

**Solution**: Use CPU-only mode
```python
# In stt.py, change:
whisper_model = whisper.load_model(WHISPER_MODEL_SIZE, device="cpu")
```

#### 5. High CPU usage

**Solution**:
- Reduce `CHUNK_DURATION` to 1.0 seconds
- Use `"tiny"` Whisper model
- Increase sleep intervals in processing loops

### Performance Optimization

#### For Low-End Hardware

```python
# In core/stt.py
WHISPER_MODEL_SIZE = "tiny"
CHUNK_DURATION = 1.0
VAD_THRESHOLD = 0.6  # Less sensitive
```

#### For High-End Hardware

```python
# In core/stt.py
WHISPER_MODEL_SIZE = "base"
CHUNK_DURATION = 3.0
VAD_THRESHOLD = 0.4  # More sensitive
```

## 📊 Performance Metrics

### Expected Performance

| Component | Latency | Accuracy | CPU Usage |
|-----------|---------|----------|-----------|
| Vosk (Live) | ~50ms | ~85% | Low |
| Whisper (Final) | ~500ms | ~95% | Medium-High |
| VAD | ~10ms | ~90% | Low |
| Total System | ~100ms | ~95% | Medium |

### Memory Usage

- **Vosk Model**: ~40MB
- **Whisper Tiny**: ~80MB
- **Whisper Base**: ~150MB
- **Silero VAD**: ~5MB
- **Total**: ~125-200MB + audio buffers

## 🎛️ Advanced Features

### Wake Word Detection (Optional)

To add wake word detection using Porcupine:

```python
# Install additional dependency
pip install pvporcupine

# In core/stt.py, uncomment:
# porcupine = create_porcupine(access_key="YOUR_ACCESS_KEY", keywords=["computer"])

# Add wake word checking in audio processing loop
```

### Custom Commands

The system integrates with the existing command system. Say:

- `"open notepad"`
- `"search python on google"`
- `"create folder test"`
- `"exit voice"` - to stop listening

### Transcript Management

```python
from core.stt import get_current_transcript, clear_transcript

# Get current transcript
transcript = get_current_transcript()

# Clear transcript
clear_transcript()
```

## 🔒 Security & Privacy

- ✅ **100% Offline** - No data sent to external servers
- ✅ **Local Processing** - All audio processed on device
- ✅ **No Cloud APIs** - No Google, AWS, or Azure dependencies
- ✅ **Memory Only** - Audio not saved to disk (unless configured)

## 📝 API Reference

### Core Functions

```python
# Start/stop the STT system
start_offline_stt() -> bool
stop_offline_stt() -> None

# Get transcript
get_current_transcript() -> str
clear_transcript() -> None

# Legacy compatibility
listen() -> Optional[str]  # Blocking call for single utterances
```

### Configuration Constants

```python
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = 2.0
OVERLAP_DURATION = 0.5
VAD_THRESHOLD = 0.5
WHISPER_MODEL_SIZE = "tiny"
```

## 🚀 Production Deployment

### Systemd Service (Linux)

Create `/etc/systemd/system/menu-ai.service`:

```ini
[Unit]
Description=Menu AI Assistant with Offline STT
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/menu-ai-2
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Windows Service

Use NSSM or create a batch file for startup.

### Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python setup_offline_stt.py

CMD ["python", "main.py"]
```

## 📞 Support

If you encounter issues:

1. Check the logs in `menu.log`
2. Run the setup script again: `python setup_offline_stt.py`
3. Test individual components:

```python
# Test audio
python -c "import sounddevice as sd; print('Audio devices:', sd.query_devices())"

# Test Whisper
python -c "import whisper; model = whisper.load_model('tiny'); print('Whisper OK')"

# Test Vosk
python -c "from vosk import Model; Model('models/vosk-model-small-en-us-0.15'); print('Vosk OK')"
```

## 🎯 What's Next

- **Wake word detection** - Add "Hey Menu" activation
- **Multi-language support** - Extend beyond English
- **Speaker identification** - Recognize different users
- **Command confidence scoring** - Only execute high-confidence commands
- **Audio preprocessing** - Noise cancellation and echo removal

---

**🎉 Your offline STT system is now ready! The assistant will provide real-time speech recognition without any internet connection.**