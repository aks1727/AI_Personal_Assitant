# utils/constants.py
from config import settings

class ImmutableMeta(type):
    """
    A metaclass that completely blocks attribute modifications 
    on the class level, perfectly mirroring Java's 'final' keyword.
    """
    def __setattr__(cls, name, value):
        raise AttributeError(f"Immutable Error: Cannot reassign final constant '{name}' on class '{cls.__name__}'.")
    
    def __delattr__(cls, name):
        raise AttributeError(f"Immutable Error: Cannot delete final constant '{name}' on class '{cls.__name__}'.")


# Apply the metaclass to your Constants blocks
class AudioConstants(metaclass=ImmutableMeta):
    TEMP_AUDIO_MP3 = settings.TEMP_AUDIO_MP3
    STABLE_PLAYER_COMMAND = f"ffplay -nodisp -autoexit -loglevel quiet {TEMP_AUDIO_MP3} 2> /dev/null"


class AssistantConfigs(metaclass=ImmutableMeta):
    VOICE_IDENTITY = "en-GB-RyanNeural"