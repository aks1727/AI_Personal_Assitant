# config/settings.py
import os

ASSISTANT_NAME = "Jarvis"
DEFAULT_VOICE = "en-GB-RyanNeural"

# Quick calibration delay for ambient audio snapshots
AMBIENT_NOISE_DURATION = 0.5
RECOGNITION_LANGUAGE = "en-IN"

TEMP_AUDIO_MP3 = "speech.mp3"
PLAYER_COMMAND = "ffplay -nodisp -autoexit -loglevel quiet"