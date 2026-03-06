import os
import shlex
import subprocess
import tempfile
from pathlib import Path

import ollama

# ---------- Configuration ----------
# Local LLM served by Ollama (local only)
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:3b")

# Local STT via whisper.cpp CLI
WHISPER_CPP_BIN = os.getenv("WHISPER_CPP_BIN", "whisper-cli")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "./models/ggml-base.en.bin")

# Local TTS via Piper
PIPER_BIN = os.getenv("PIPER_BIN", "piper")
PIPER_MODEL = os.getenv("PIPER_MODEL", "./en_US-lessac-medium.onnx")

# Audio capture/playback (PipeWire/PulseAudio routed to Bluetooth headset)
MIC_SAMPLE_RATE = int(os.getenv("MIC_SAMPLE_RATE", "16000"))
MAX_RECORD_SECONDS = int(os.getenv("MAX_RECORD_SECONDS", "8"))

# Optional Hailo AI HAT 2.0 compatibility checks
HAILO_CHECK = os.getenv("HAILO_CHECK", "1") not in {"0", "false", "False"}
HAILO_RT_BIN = os.getenv("HAILO_RT_BIN", "hailortcli")

EXIT_WORDS = {"exit", "quit", "goodbye", "stop"}


def run_cmd(command: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return completed process."""
    return subprocess.run(
        command,
        shell=True,
        check=check,
        text=True,
        capture_output=True,
    )


def record_user_audio(wav_path: Path) -> bool:
    """Record mono 16kHz audio from default input device."""
    cmd = (
        f"timeout {MAX_RECORD_SECONDS}s "
        f"pw-record --format=s16 --rate={MIC_SAMPLE_RATE} --channels=1 {shlex.quote(str(wav_path))}"
    )
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return wav_path.exists() and wav_path.stat().st_size > 0 and result.returncode in (0, 124)


def transcribe_with_whisper(audio_path: Path) -> str:
    """Run local whisper.cpp and return transcript text."""
    out_txt = audio_path.with_suffix("")
    cmd = (
        f"{shlex.quote(WHISPER_CPP_BIN)} "
        f"-m {shlex.quote(WHISPER_MODEL)} "
        f"-f {shlex.quote(str(audio_path))} "
        f"-otxt -of {shlex.quote(str(out_txt))} -np"
    )
    result = run_cmd(cmd, check=False)
    transcript_file = Path(f"{out_txt}.txt")

    if result.returncode != 0 or not transcript_file.exists():
        return ""

    text = transcript_file.read_text(encoding="utf-8").strip()
    transcript_file.unlink(missing_ok=True)
    return text


def speak_text(text: str) -> None:
    """Synthesize local TTS with Piper and play to default output (Bluetooth sink)."""
    clean = text.strip()
    if not clean:
        return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)

    try:
        tts_cmd = (
            f"echo {shlex.quote(clean)} | "
            f"{shlex.quote(PIPER_BIN)} --model {shlex.quote(PIPER_MODEL)} "
            f"--output_file {shlex.quote(str(wav_path))}"
        )
        run_cmd(tts_cmd)
        run_cmd(f"pw-play {shlex.quote(str(wav_path))}")
    finally:
        wav_path.unlink(missing_ok=True)


def chat_once(user_text: str) -> str:
    """Query local Ollama model and return response."""
    response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a concise, helpful Raspberry Pi voice assistant.",
            },
            {"role": "user", "content": user_text},
        ],
    )
    return response["message"]["content"].strip()


def check_prereqs() -> None:
    if not Path(WHISPER_MODEL).exists():
        raise FileNotFoundError(f"Whisper model not found: {WHISPER_MODEL}")
    if not Path(PIPER_MODEL).exists():
        raise FileNotFoundError(f"Piper model not found: {PIPER_MODEL}")


def check_hailo_runtime() -> None:
    """Best-effort check for an installed Hailo runtime/device."""
    if not HAILO_CHECK:
        return

    probe_cmd = f"{shlex.quote(HAILO_RT_BIN)} scan"
    result = subprocess.run(probe_cmd, shell=True, text=True, capture_output=True)

    if result.returncode == 0:
        print("[Hailo runtime detected. AI HAT compatibility check passed.]")
        return

    print("[Hailo runtime not detected. Continuing in CPU-only local mode.]")
    print(
        "[Tip] Install HailoRT and ensure 'hailortcli scan' succeeds on your Pi 5 + "
        "Hailo-10H AI HAT 2.0 setup if accelerator offload is required."
    )


def main() -> None:
    check_prereqs()
    check_hailo_runtime()

    print("=== Raspberry Pi 5 Local Voice Chatbot ===")
    print(f"LLM Model: {LLM_MODEL}")
    print("Speak after each [Listening...] prompt.")

    while True:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            mic_wav = Path(tmp.name)

        try:
            print("\n[Listening...]")
            if not record_user_audio(mic_wav):
                print("[No audio captured. Check Bluetooth mic/input routing.]")
                continue

            user_text = transcribe_with_whisper(mic_wav)
            if not user_text:
                print("[STT failed or no speech detected.]")
                continue

            print(f"You: {user_text}")

            if user_text.lower().strip() in EXIT_WORDS:
                speak_text("Goodbye!")
                break

            ai_text = chat_once(user_text)
            print(f"AI: {ai_text}")
            speak_text(ai_text)

        finally:
            mic_wav.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")
