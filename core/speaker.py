# core/speaker.py
import os
import asyncio
import edge_tts
from config import settings
from utils.constants import AudioConstants

class VoiceSpeaker:
    def __init__(self, voice_identity: str = settings.DEFAULT_VOICE):
        self.default_voice = voice_identity
        
        # --- MULTILINGUAL VOICE PROFILE MAP ---
        # Maps the language code detected by Whisper to a highly localized Edge-TTS voice actor
        self.voice_map = {
            "en": "en-GB-RyanNeural",       # Sophisticated British English
            "hi": "hi-IN-MadhurNeural",     # Natural Male Hindi (India)
            "bn": "bn-IN-BashkarNeural",    # Natural Male Bengali (India)
            "ko": "ko-KR-InJoonNeural",     # Natural Male Korean
            "ja": "ja-JP-KeitaNeural",      # Natural Male Japanese
            "es": "es-ES-AlvaroNeural"      # Natural Male Spanish (Spain)
        }

    def speak(self, text: str, language_code: str = "en"):
        """Speaks text out loud using a voice matched to the active language choice."""
        print(f"{settings.ASSISTANT_NAME}: {text}")
        asyncio.run(self._generate_and_play(text, language_code))

    async def _generate_and_play(self, text: str, language_code: str):
        try:
            # 1. Look up the language code or default back to your classic British Jarvis voice
            selected_voice = self.voice_map.get(language_code.lower(), self.default_voice)
            
            padded_text = f", , {text}"
            communicate = edge_tts.Communicate(padded_text, selected_voice)
            await communicate.save(AudioConstants.TEMP_AUDIO_MP3)
            
            os.system(AudioConstants.STABLE_PLAYER_COMMAND)
            
        except Exception as e:
            print(f"\n[Playback Failure: {e}]")
        finally:
            self._cleanup_temp_files()

    def _cleanup_temp_files(self):
        if os.path.exists(AudioConstants.TEMP_AUDIO_MP3):
            os.remove(AudioConstants.TEMP_AUDIO_MP3)