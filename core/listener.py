# core/speaker.py

import os

import asyncio

import edge_tts

from config import settings



class VoiceSpeaker:

    def __init__(self, voice_identity: str = settings.DEFAULT_VOICE):

        self.voice_identity = voice_identity



    def set_voice(self, voice_name: str):

        """Allows runtime switching of voice profiles using database keys."""

        self.voice_identity = voice_name



    def speak(self, text: str):

        """Standard synchronous wrapper to handle the internal async processing loop."""

        print(f"{settings.ASSISTANT_NAME}: {text}")

        asyncio.run(self._generate_and_play(text))



    async def _generate_and_play(self, text: str):

        """Leverages cloud neural synthesis to generate a clean vocal stream."""

        try:

            communicate = edge_tts.Communicate(text, self.voice_identity)

            await communicate.save(settings.TEMP_AUDIO_MP3)

            

            # SURGICAL OS FIX: Append '2> /dev/null' directly to the player sequence execution.

            # This completely mutes the ALSA/JACK warnings fired during audio initialization.

            silent_player_command = f"{settings.PLAYER_COMMAND} {settings.TEMP_AUDIO_MP3} 2> /dev/null"

            os.system(silent_player_command)

            

        except Exception as e:

            print(f"\n[Playback Pipeline Failure: {e}]")

        finally:

            # Clean up disk footprint instantly

            self._cleanup_temp_files()



    def _cleanup_temp_files(self):

        """Removes local cached binaries to keep working spaces clear."""

        if os.path.exists(settings.TEMP_AUDIO_MP3):

            os.remove(settings.TEMP_AUDIO_MP3)