# Urdu Voice Command Assistant 🎙️🇵🇰

A desktop application that lets you control your PC using Urdu voice commands.

## Features
- Recognize Urdu speech using a fine-tuned Wav2Vec2 model
- Control system functions like:
  - Brightness
  - Volume
  - Bluetooth / Wi-Fi
  - Open apps (Notepad, Chrome, WhatsApp, Spotify)
- Smart fuzzy matching for similar commands
- Simple and clean PyQt5 GUI

## Getting Started

### Requirements
- Python 3.8+
- PyTorch
- PyQt5
- Transformers
- RapidFuzz
- SoundDevice
- ScreenBrightnessControl
- pycaw

### Installation
```bash
pip install -r requirements.txt
python nlp.py
