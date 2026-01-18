import ollama
import speech_recognition as sr
import subprocess
import re
import os

# Configuration
MODEL = "llama3.2"  # Fast on Pi 5
VOICE_MODEL = "en_US-lessac-medium.onnx"  # You need to download this file

def speak_streaming(text_chunk):
    # The -D flag tells aplay which device to use
    command = f'echo "{text_chunk}" | piper --model {VOICE_MODEL} --output_raw | aplay -D bluealsa -r 22050 -f S16_LE'
    subprocess.run(command, shell=True)
    
def listen_and_respond():
    recognizer = sr.Recognizer()
    
    with sr.Microphone(device_index=1, sample_rate=16000) as source:
        # Calibrate for your Bluetooth mic's background noise
        print("\n--- Calibrating mic... ---")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("[Ready! Speak into your earphones...]")
        
        try:
            # Captures audio from your Bluetooth headset
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            # Transcription (Sends audio to Google for fast text conversion)
            user_input = recognizer.recognize_google(audio)
            print(f"You: {user_input}")
            
            # Streaming LLM Response
            print("AI: ", end="", flush=True)
            stream = ollama.chat(model=MODEL, messages=[{'role': 'user', 'content': user_input}], stream=True)
            
            sentence_buffer = ""
            for chunk in stream:
                content = chunk['message']['content']
                print(content, end="", flush=True)
                sentence_buffer += content
                
                # Check for end of a sentence to start speaking immediately
                if any(p in content for p in ".!?"):
                    sentences = re.split(r'(?<=[.!?]) +', sentence_buffer)
                    if len(sentences) > 1:
                        speak_streaming(sentences[0])
                        sentence_buffer = sentences[1]
            
            # Speak anything remaining in the buffer
            if sentence_buffer.strip():
                speak_streaming(sentence_buffer)

        except sr.UnknownValueError:
            print("\n[System: Could not understand audio. Try speaking closer to the mic.]")
        except Exception as e:
            print(f"\n[System Error: {e}]")

if __name__ == "__main__":
    # Check if you have the Piper model file in the folder
    if not os.path.exists(VOICE_MODEL):
        print(f"Error: {VOICE_MODEL} not found.")
        print("Download it: wget https://github.com/rhasspy/piper/releases/download/v1.0.0/en_US-lessac-medium.onnx")
    else:
        while True:
            listen_and_respond()