# Raspberry Pi 5 + HALO HAT 2.0 Local Voice Chatbot

This project gives you a **fully local voice pipeline**:

1. Bluetooth headset microphone input
2. Local speech-to-text (Whisper.cpp)
3. Local LLM call (Ollama)
4. Local text-to-speech (Piper)
5. Playback to Bluetooth headphones

> Notes on HALO HAT 2.0:
> - The script is local-first and runs entirely on your Pi.
> - Actual accelerator offload depends on the model/runtime support you install on the HAT stack.
> - Ollama works locally on Pi CPU/GPU stack; if your HALO runtime exposes compatible LLM acceleration, use that model/runtime in place of default.

## 1) System packages

```bash
sudo apt update
sudo apt install -y python3-pip pipewire pipewire-audio-client-libraries pulseaudio-utils ffmpeg
```

## 2) Python packages

```bash
pip install ollama
```

## 3) Install Ollama (local LLM)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
```

## 4) Install Whisper.cpp (local STT)

Build or install `whisper-cli` so it is available in PATH, then download a model:

```bash
mkdir -p models
wget -O models/ggml-base.en.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
```

## 5) Install Piper (local TTS)

Install `piper` binary and download a free voice model:

```bash
wget -O en_US-lessac-medium.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget -O en_US-lessac-medium.onnx.json \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

## 6) Pair and route Bluetooth headset

1. Pair headset (using desktop Bluetooth settings or `bluetoothctl`).
2. Set your headset profile to include microphone (HFP/HSP) if you need mic input.
3. Verify defaults:

```bash
pw-cli ls Node | rg -i "blue|headset|handsfree"
pactl get-default-source
pactl get-default-sink
```

If needed, set defaults manually:

```bash
pactl set-default-source <your_bt_mic_source>
pactl set-default-sink <your_bt_headphone_sink>
```

## 7) Run

```bash
python3 chat.py
```

## Optional environment variables

```bash
export LLM_MODEL="llama3.2:3b"
export WHISPER_CPP_BIN="whisper-cli"
export WHISPER_MODEL="./models/ggml-base.en.bin"
export PIPER_BIN="piper"
export PIPER_MODEL="./en_US-lessac-medium.onnx"
export MAX_RECORD_SECONDS=8
```

Then run again:

```bash
python3 chat.py
```

## Troubleshooting

- If you hear output but STT fails, headset may be on A2DP-only profile (no mic). Switch to HFP/HSP profile.
- If STT is slow, use `ggml-tiny.en.bin` for faster transcription.
- If TTS is slow, use a smaller Piper model or shorter responses.
- Confirm local-only behavior by disconnecting internet after models are already downloaded.
