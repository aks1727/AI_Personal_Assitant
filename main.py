# main.py
import sys
import time
import json
from core.listener import SpeechListener
from core.brain import AssistantBrain
from core.speaker import VoiceSpeaker 
from config import settings

TELEMETRY_PATH = "diagnostics.json"

def export_telemetry(data: dict):
    try:
        with open(TELEMETRY_PATH, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[Telemetry Export Failed: {e}]")

def run_system_diagnostics(voice, ears):
    print("\n========================================")
    print(" >> RUNNING HARDWARE DIAGNOSTIC MATRIX <<")
    print("========================================")
    
    voice.speak("Running diagnostics for your audio environment, sir.", language_code="en")
    time.sleep(0.1)
    
    try:
        # Extract fully dynamic Z-Score metrics
        noise_mean = getattr(ears, 'HF_NOISE_MEAN', 0.0)
        noise_std = getattr(ears, 'HF_NOISE_STD', 0.0)
        energy_gate = getattr(ears, 'HF_ENERGY_GATE', 0.0)
        sustain_gate = getattr(ears, 'HF_SUSTAIN_GATE', 0.0)
        
        if noise_mean <= 0.0:
            raise ValueError("Microphone channel returned flatline zero vectors.")
            
        print(f"[Hardware Pass] Acoustic pipeline verified. Wind Mean: {int(noise_mean)}")
        print(f"[Auto-Tuning] Trigger locked to: {int(energy_gate)} | Sustain locked to: {int(sustain_gate)}")
        
        telemetry_payload = {
            "status": "Online",
            "timestamp": time.time(),
            "os_environment": sys.platform,
            "audio": {
                "sample_rate": ears.RATE,
                "frame_chunk": ears.CHUNK,
                "hf_noise_mean": int(noise_mean),
                "hf_noise_std_dev": int(noise_std),
                "dynamic_trigger_gate": int(energy_gate),
                "dynamic_sustain_gate": int(sustain_gate)
            },
            "models": {
                "stt_engine": ears.model_name,
                "llm_engine": "llama3.2"
            }
        }
        
        export_telemetry(telemetry_payload)
        voice.speak("Audio environment checks are complete. Acoustic channels are balanced.", language_code="en")
        
    except Exception as e:
        print(f"\n[CRITICAL INITIALIZATION ANOMALY]: {e}")
        voice.speak("Warning, sir. Audio engine layers failed a critical hardware interface handshake.", language_code="en")
        export_telemetry({"status": "Offline", "error": str(e)})
        sys.exit(1)

    print("========================================\n")
    voice.speak("Systems are fully active and online.", language_code="en")

def main():
    voice = VoiceSpeaker()
    ears = SpeechListener()
    brain = AssistantBrain()

    run_system_diagnostics(voice, ears)

    while True:
        try:
            query, detected_lang, complexity_tier = ears.listen()

            if query == "None" or not query.strip():
                continue

            if "shutdown" in query.lower() or "goodbye" in query.lower():
                voice.speak("Powering down system layers. Safe travels, sir.", language_code="en")
                export_telemetry({"status": "Offline", "reason": "Shut down by user"})
                break

            reply, reply_lang = brain.generate_response(query, complexity_tier, detected_lang)
            voice.speak(reply, language_code=reply_lang)

        except KeyboardInterrupt:
            print("\n[System Status: Interrupted by User. Exiting...]")
            export_telemetry({"status": "Offline", "reason": "User Interrupted"})
            break
        except Exception as e:
            continue

if __name__ == "__main__":
    main()