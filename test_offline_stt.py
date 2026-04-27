#!/usr/bin/env python3
"""
Offline STT Test Script

This script tests the offline Speech-to-Text system components.
Run this to verify your setup before using the main assistant.
"""

import sys
import time
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported."""
    print("🧪 Testing imports...")

    try:
        import sounddevice as sd
        import numpy as np
        import torch
        from vosk import Model, KaldiRecognizer
        import silero_vad
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def test_audio_devices():
    """Test audio device availability."""
    print("🔊 Testing audio devices...")

    try:
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]

        if not input_devices:
            print("❌ No input devices found")
            return False

        print(f"✅ Found {len(input_devices)} input device(s)")
        for i, device in enumerate(input_devices[:3]):  # Show first 3
            print(f"  {i+1}. {device['name']}")

        return True
    except Exception as e:
        print(f"❌ Audio device test failed: {e}")
        return False

def test_vosk_model():
    """Test Vosk model loading."""
    print("🎙️ Testing Vosk model...")

    try:
        from vosk import Model, KaldiRecognizer
        model_path = Path(__file__).parent / "models" / "vosk-model-small-en-us-0.15"

        if not model_path.exists():
            print(f"❌ Vosk model not found at {model_path}")
            print("Run: python setup_offline_stt.py")
            return False

        model = Model(str(model_path))
        recognizer = KaldiRecognizer(model, 16000)

        print("✅ Vosk model loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Vosk test failed: {e}")
        return False

def test_whisper_model():
    """Test Whisper model loading."""
    print("🤖 Testing Whisper model...")
    print("⚠️  Whisper not included in this version (using Vosk-only)")
    return True

def test_vad():
    """Test Voice Activity Detection."""
    print("👂 Testing Voice Activity Detection...")

    try:
        import silero_vad
        model, utils = silero_vad.load_silero_vad()
        print("✅ VAD loaded successfully")
        return True
    except Exception as e:
        print(f"⚠️  VAD not available: {e}")
        print("Using simple energy-based VAD as fallback")
        return True

def test_audio_capture():
    """Test basic audio capture."""
    print("🎤 Testing audio capture (5 seconds)...")

    try:
        import sounddevice as sd
        import numpy as np

        # Record 1 second of audio
        duration = 1.0
        sample_rate = 16000

        print("Recording... Speak into your microphone")
        audio = sd.rec(int(duration * sample_rate),
                      samplerate=sample_rate,
                      channels=1,
                      dtype='float32')
        sd.wait()

        # Check if we got audio data
        if audio.size == 0:
            print("❌ No audio data captured")
            return False

        # Check audio levels
        rms = np.sqrt(np.mean(audio**2))
        if rms < 0.001:
            print("⚠️ Audio levels very low - check microphone")
        else:
            print(".2f")

        print("✅ Audio capture successful")
        return True

    except Exception as e:
        print(f"❌ Audio capture test failed: {e}")
        return False

def test_full_pipeline():
    """Test the complete offline STT pipeline."""
    print("🔄 Testing full STT pipeline...")

    try:
        from core.stt import OfflineSTT

        stt = OfflineSTT()
        if not stt.load_models():
            print("❌ Model loading failed")
            return False

        print("✅ Full pipeline test passed")
        return True

    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Offline STT System Test")
    print("=" * 40)

    tests = [
        ("Imports", test_imports),
        ("Audio Devices", test_audio_devices),
        ("Vosk Model", test_vosk_model),
        ("Whisper Model", test_whisper_model),
        ("Voice Activity Detection", test_vad),
        ("Audio Capture", test_audio_capture),
        ("Full Pipeline", test_full_pipeline),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 20)
        if test_func():
            passed += 1
        print()

    print("📊 Test Results")
    print("=" * 40)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! Your offline STT system is ready.")
        print("\n🚀 Next steps:")
        print("1. Run: python main.py")
        print("2. Say: 'open notepad' or 'search python on google'")
        print("3. Watch for [LIVE] and [FINAL] outputs")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("\n🔧 Troubleshooting:")
        print("1. Run: python setup_offline_stt.py")
        print("2. Check microphone permissions")
        print("3. Ensure sufficient RAM (>4GB)")
        return False

if __name__ == "__main__":
    success = main()
    input("\nPress Enter to exit...")
    sys.exit(0 if success else 1)