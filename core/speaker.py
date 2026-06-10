import os
import asyncio
import subprocess
import edge_tts
from utils.constants import Settings


class VoiceSpeaker:
    def __init__(self, voice_identity: str = Settings.DEFAULT_VOICE):
        self.voice_identity = voice_identity

    def set_voice(self, voice_name: str):
        """Runtime voice switching using database keys."""
        self.voice_identity = voice_name

    def speak(self, text: str):
        """Synchronous entry point — wraps the async TTS pipeline."""
        print(f"{Settings.ASSISTANT_NAME}: {text}")

        # On Windows, a running event loop already exists in some environments.
        # asyncio.run() raises RuntimeError in that case — use get_event_loop instead.
        try:
            loop = asyncio.get_running_loop()
            # Already inside a running loop (e.g. Jupyter, some Windows configs)
            loop.run_until_complete(self._generate_and_play(text))
        except RuntimeError:
            # No running loop — safe to use asyncio.run() directly
            asyncio.run(self._generate_and_play(text))

    async def _generate_and_play(self, text: str):
        """Generate speech via Edge-TTS, play via ffplay, clean up."""
        try:
            communicate = edge_tts.Communicate(text, self.voice_identity)
            await communicate.save(Settings.TEMP_AUDIO_MP3)
            self._play_audio(Settings.TEMP_AUDIO_MP3)
        except Exception as e:
            print(f"[Speaker error: {e}]")
        finally:
            self._cleanup()

    @staticmethod
    def _play_audio(filepath: str):
        cmd = [
            "ffplay",
            "-nodisp",
            "-autoexit",
            "-loglevel",
            "quiet",
            filepath,
        ]
        try:
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,  # don't raise on non-zero exit
            )
        except FileNotFoundError:
            print("[Speaker] ffplay not found. Install ffmpeg and ensure it's on PATH.")
        except Exception as e:
            print(f"[Speaker] Playback error: {e}")

    def _cleanup(self):
        """Remove the temp MP3 after playback."""
        try:
            if os.path.exists(Settings.TEMP_AUDIO_MP3):
                os.remove(Settings.TEMP_AUDIO_MP3)
        except Exception as e:
            print(f"[DEBUG] {e}")
