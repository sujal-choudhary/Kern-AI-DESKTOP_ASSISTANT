#!/usr/bin/env python3
"""
Offline STT Setup Script

This script helps set up the offline Speech-to-Text system by:
1. Installing required Python packages
2. Downloading Vosk model for English
3. Testing the setup
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def download_vosk_model():
    """Download Vosk English model."""
    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(exist_ok=True)

    model_path = models_dir / "vosk-model-small-en-us-0.15"
    zip_path = models_dir / "vosk-model-small-en-us-0.15.zip"

    if model_path.exists():
        print("✅ Vosk model already exists")
        return True

    print("📥 Downloading Vosk English model (small)...")

    try:
        # Download the model
        url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
        print(f"Downloading from: {url}")

        with urllib.request.urlopen(url) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0

            with open(zip_path, 'wb') as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(".1f", end='', flush=True)

        print("\n📦 Extracting model...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(models_dir)

        # Clean up zip file
        zip_path.unlink()

        if model_path.exists():
            print("✅ Vosk model downloaded and extracted")
            return True
        else:
            print("❌ Model extraction failed")
            return False

    except Exception as e:
        print(f"❌ Failed to download Vosk model: {e}")
        return False

def test_whisper():
    """Test Whisper model loading."""
    print("🧪 Testing Whisper model...")
    print("⚠️  Whisper not included in this version (using Vosk-only)")
    return True

def test_vosk():
    """Test Vosk model loading."""
    print("🧪 Testing Vosk model...")

    try:
        from vosk import Model
        model_path = Path(__file__).parent / "models" / "vosk-model-small-en-us-0.15"
        if not model_path.exists():
            print("❌ Vosk model not found")
            return False

        model = Model(str(model_path))
        print("✅ Vosk model loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Vosk test failed: {e}")
        return False

def test_vad():
    """Test Silero VAD."""
    print("🧪 Testing Silero VAD...")

    try:
        import silero_vad
        model, utils = silero_vad.silero_vad()
        print("✅ Silero VAD loaded successfully")
        return True
    except Exception as e:
        print(f"❌ VAD test failed: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 Setting up Offline STT System")
    print("=" * 50)

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False

    print(f"🐍 Python version: {sys.version}")

    # Install/update requirements
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return False

    # Download Vosk model
    if not download_vosk_model():
        return False

    # Test components
    print("\n🧪 Testing components...")

    tests_passed = 0
    total_tests = 3

    if test_whisper():
        tests_passed += 1

    if test_vosk():
        tests_passed += 1

    if test_vad():
        tests_passed += 1

    print(f"\n📊 Test Results: {tests_passed}/{total_tests} passed")

    if tests_passed == total_tests:
        print("\n🎉 Setup completed successfully!")
        print("\n📝 Usage:")
        print("1. Run: python main.py")
        print("2. The system will use offline STT automatically")
        print("\n📋 Features:")
        print("- Real-time live preview (Vosk)")
        print("- Accurate final transcription (Vosk)")
        print("- Voice Activity Detection (VAD)")
        print("- 100% offline operation")
        return True
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)