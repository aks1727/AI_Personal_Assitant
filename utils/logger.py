import os
from contextlib import contextmanager

@contextmanager
def silence_alsa_errors():
    """Surgically blocks low-level C stderr outputs (ALSA/JACK) while keeping Python errors active."""
    # Open a pointer to the system null device
    devnull = os.open(os.devnull, os.O_WRONLY)
    # Duplicate standard error file descriptor to restore it later
    old_stderr = os.dup(2)
    
    try:
        # Redirect raw hardware driver stderr to devnull
        os.dup2(devnull, 2)
        yield
    finally:
        # Restore original system stderr definitions immediately after the block
        os.dup2(old_stderr, 2)
        os.close(devnull)
        os.close(old_stderr)