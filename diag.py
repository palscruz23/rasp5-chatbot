import speech_recognition as sr

def simple_test():
    r = sr.Recognizer()
    # By not specifying an index, it uses the system default 
    # (The same one Gemini is using right now)
    with sr.Microphone() as source:
        print("System Default Mic found. Speak now...")
        # Adjusting for noise is crucial for Bluetooth
        r.adjust_for_ambient_noise(source, duration=1)
        
        try:
            audio = r.listen(source, timeout=5)
            print("Transcribing...")
            text = r.recognize_google(audio)
            print(f"Result: {text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    simple_test()