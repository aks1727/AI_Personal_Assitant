import sys
import time
import json
from core.listener import SpeechListener
from core.brain import AssistantBrain
from core.speaker import VoiceSpeaker

TELEMETRY_PATH = "diagnostics.json"


def export_telemetry(data: dict):
    try:
        with open(TELEMETRY_PATH, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[Telemetry Export Failed: {e}]")


def run_system_diagnostics(voice: VoiceSpeaker, ears: SpeechListener):
    print("\n========================================")
    print(" >> RUNNING HARDWARE DIAGNOSTIC MATRIX <<")
    print("========================================")

    voice.speak("Running diagnostics for your audio environment, sir.")
    time.sleep(0.1)

    try:
        # Use the built-in diagnostics method — single source of truth
        diag = ears.get_diagnostics()

        # Sanity check: a real mic will never produce a zero mean
        if diag["hf_mean"] <= 0.0:
            raise ValueError("Microphone channel returned flatline zero vectors.")

        print(
            f"[Hardware Pass] Acoustic pipeline verified. Wind Mean: {int(diag['hf_mean'])}"
        )
        print(
            f"[Auto-Tuning]   Trigger: {int(diag['trigger_gate'])} | Sustain: {int(diag['sustain_gate'])}"
        )

        telemetry_payload = {
            "status": "Online",
            "timestamp": time.time(),
            "os_environment": sys.platform,
            "audio": {
                "sample_rate": diag["rate"],
                "frame_chunk": diag["chunk"],
                "hf_noise_mean": int(diag["hf_mean"]),
                "hf_noise_std_dev": int(diag["hf_std"]),
                "dynamic_trigger_gate": int(diag["trigger_gate"]),
                "dynamic_sustain_gate": int(diag["sustain_gate"]),
            },
            "models": {
                "stt_engine": "faster-whisper-base",
                "llm_engine": "llama3.2",
            },
        }

        export_telemetry(telemetry_payload)
        voice.speak(
            "Audio environment checks are complete. Acoustic channels are balanced."
        )

    except Exception as e:
        print(f"\n[CRITICAL INITIALIZATION ANOMALY]: {e}")
        voice.speak(
            "Warning, sir. Audio engine layers failed a critical hardware interface handshake."
        )
        export_telemetry({"status": "Offline", "error": str(e)})
        sys.exit(1)

    print("========================================\n")
    voice.speak("Systems are fully active and online.")


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
                voice.speak("Powering down system layers. Safe travels, sir.")
                export_telemetry({"status": "Offline", "reason": "Shut down by user"})
                ears.shutdown()
                break

            reply, reply_lang = brain.generate_response(
                query, complexity_tier, detected_lang
            )
            voice.speak(reply)

        except KeyboardInterrupt:
            print("\n[System Status: Interrupted by User. Exiting...]")
            export_telemetry({"status": "Offline", "reason": "User Interrupted"})
            ears.shutdown()
            break

        except Exception as e:
            print(f"[Loop error: {e}]")
            continue


if __name__ == "__main__":
    main()
