import ollama
import speech_recognition as sr
import subprocess
import re
import os
import shlex

# --- CONFIGURATION ---
MODEL = "llama3.2"
VOICE_MODEL = "en_US-lessac-medium.onnx"
TEMP_SPEECH_FILE = "ai_resp.wav"
TEMP_MIC_FILE = "user_voice.wav"

def speak_sentence(text_chunk):
    """Converts a text chunk to speech and plays it via PipeWire."""
    if not text_chunk.strip():
        return
    
    # shlex.quote handles apostrophes and special characters in AI text
    safe_text = shlex.quote(text_chunk)
    
    try:
        # Generate the audio file
        subprocess.run(f'echo {safe_text} | piper --model {VOICE_MODEL} --output_file {TEMP_SPEECH_FILE}', 
                       shell=True, check=True, stderr=subprocess.DEVNULL)
        
        # Play via Native PipeWire player (pw-play)
        subprocess.run(f'pw-play {TEMP_SPEECH_FILE}', shell=True, check=True)
        
    except Exception as e:
        print(f"\n[Playback Error] {e}")
    finally:
        if os.path.exists(TEMP_SPEECH_FILE):
            os.remove(TEMP_SPEECH_FILE)

def listen_to_user():
    """Records audio using the timeout utility to ensure it stops."""
    if os.path.exists(TEMP_MIC_FILE):
        os.remove(TEMP_MIC_FILE)
    
    print("\n[Listening... Speak into your headset]")
    
    try:
        # Use 'timeout 5s' to force the recording to finish
        # We use --format=s16 as it's the standard for Bluetooth headsets
        record_cmd = f"timeout 5s pw-record --format=s16 --rate=16000 --channels=1 {TEMP_MIC_FILE}"
        
        # Run the command and wait for the 5-second timeout
        subprocess.run(record_cmd, shell=True, check=False, stderr=subprocess.DEVNULL)

        if not os.path.exists(TEMP_MIC_FILE):
            print("[Mic Error] No audio file created.")
            return None

        # Transcribe the file
        r = sr.Recognizer()
        with sr.AudioFile(TEMP_MIC_FILE) as source:
            audio_data = r.record(source)
            print("Transcribing...")
            text = r.recognize_google(audio_data)
            return text
            
    except sr.UnknownValueError:
        print("AI: I couldn't understand that. Try again?")
    except Exception as e:
        print(f"[Speech Error] {e}")
    finally:
        if os.path.exists(TEMP_MIC_FILE):
            os.remove(TEMP_MIC_FILE)
    return None

def main():
    print("--- Raspberry Pi AI Chatbot (Voice-to-Voice) ---")
    print(f"Using Model: {MODEL}")
    
    # Verify voice model exists
    if not os.path.exists(VOICE_MODEL):
        print(f"FATAL: {VOICE_MODEL} not found in this folder!")
        return

    while True:
        # 1. Capture User Voice
        user_input = listen_to_user()
        
        if not user_input:
            continue
            
        print(f"You: {user_input}")
        
        if user_input.lower() in ['exit', 'quit', 'goodbye']:
            speak_sentence("Goodbye!")
            break
            
        # 2. Get Response from Ollama
        print("AI: ", end="", flush=True)
        sentence_buffer = ""
        
        stream = ollama.chat(model=MODEL, messages=[{'role': 'user', 'content': user_input}], stream=True)
        
        for chunk in stream:
            content = chunk['message']['content']
            print(content, end="", flush=True)
            sentence_buffer += content
            
            # 3. Speak as soon as a punctuation mark is reached (Low Latency)
            if any(p in content for p in ".,!?"):
                parts = re.split(r'(?<=[.,!?]) +', sentence_buffer)
                if len(parts) > 1:
                    speak_sentence(parts[0])
                    sentence_buffer = parts[1]
        
        # Speak the final remaining fragment
        if sentence_buffer.strip():
            speak_sentence(sentence_buffer)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram closed by user.")