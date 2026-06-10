# core/listener.py
#
# ARCHITECTURE:
#   - Stream opens ONCE at __init__ and stays open (no per-call open/close overhead)
#   - Standby loop runs continuously, processing tiny 30ms chunks via diff+zscore
#   - Trigger threshold: 2 consecutive speech frames (was 9) → ~60ms latency to open
#   - Silence gate: 8 frames (240ms) of quiet closes recording (was 450ms)
#   - Cross-platform: PyAudio error suppression is OS-aware (no Linux-only assumptions)

import sys
import os
import pyaudio
import webrtcvad
import collections
import time
import numpy as np
from faster_whisper import WhisperModel
from utils.constants import Settings


# ---------------------------------------------------------------------------
# Cross-platform ALSA/audio error suppressor
# ---------------------------------------------------------------------------

from contextlib import contextmanager

@contextmanager
def suppress_audio_errors():
    """
    On Linux: redirects stderr at the C-library level to silence ALSA/JACK spam.
    On Windows/macOS: no-op (those platforms don't emit ALSA noise).
    """
    if sys.platform != "linux":
        yield
        return

    # Linux: suppress C-level stderr (ALSA writes directly, bypassing Python)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    old_stderr_fd = os.dup(2)
    try:
        os.dup2(devnull_fd, 2)
        yield
    finally:
        os.dup2(old_stderr_fd, 2)
        os.close(devnull_fd)
        os.close(old_stderr_fd)


# ---------------------------------------------------------------------------
# SpeechListener
# ---------------------------------------------------------------------------

class SpeechListener:

    # ------------------------------------------------------------------
    # Audio constants
    # ------------------------------------------------------------------
    FORMAT   = pyaudio.paInt16
    CHANNELS = 1
    RATE     = 16000
    CHUNK    = 480          # 30 ms per frame  (16000 × 0.030)

    # ------------------------------------------------------------------
    # VAD tuning  ← all latency-sensitive knobs live here
    # ------------------------------------------------------------------
    CALIB_WARMUP_FRAMES  = 5    # throwaway frames at stream open
    CALIB_SAMPLE_FRAMES  = 40   # frames used to build noise profile

    TRIGGER_SIGMA        = 4.0  # z-score multiple to OPEN mic
    SUSTAIN_SIGMA        = 1.0  # z-score multiple to KEEP mic open

    # Trigger: need this many consecutive speech frames to confirm voice
    # 2 frames = 60 ms  (was effectively 9 frames / 270 ms)
    TRIGGER_CONSECUTIVE  = 2

    # Silence: close mic after this many silent frames
    # 8 frames = 240 ms  (was 15 frames / 450 ms)
    SILENCE_LIMIT        = 8

    # Pre-roll: frames kept in ring buffer prepended to recording
    # Captures the very start of the utterance that fired the trigger
    PREROLL_FRAMES       = 4    # 120 ms look-back

    def __init__(self):
        print("[Acoustic Module] Booting Dynamic Statistical VAD...")

        # --- Whisper STT ---
        self.model = WhisperModel("base", device="cpu", compute_type="int8")

        # --- PyAudio ---
        with suppress_audio_errors():
            self.pa = pyaudio.PyAudio()

        # --- WebRTC VAD (mode 3 = most aggressive) ---
        self.vad = webrtcvad.Vad(3)

        # --- Calibrate noise floor ---
        self._calibrate()

        # --- Open persistent stream (reused across every listen() call) ---
        with suppress_audio_errors():
            self._stream = self.pa.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
            )

        print("[Acoustic Module] Ready. Stream is persistent and always-on.")

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def _calibrate(self):
        """Profile the room's high-frequency ambient noise floor."""
        print("[Acoustic Module] Profiling ambient noise (keep room at idle)...")

        with suppress_audio_errors():
            calib_stream = self.pa.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
            )

        # Warm up: discard first few frames (hardware settling transients)
        for _ in range(self.CALIB_WARMUP_FRAMES):
            try:
                calib_stream.read(self.CHUNK, exception_on_overflow=False)
            except Exception:
                pass

        # Collect HF-RMS samples
        hf_samples = []
        for _ in range(self.CALIB_SAMPLE_FRAMES):
            try:
                raw = calib_stream.read(self.CHUNK, exception_on_overflow=False)
                arr = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
                if len(arr) > 1:
                    hf_samples.append(np.sqrt(np.mean(np.diff(arr) ** 2)))
            except Exception:
                pass

        calib_stream.stop_stream()
        calib_stream.close()

        self.HF_MEAN = float(np.mean(hf_samples)) if hf_samples else 100.0
        self.HF_STD  = float(np.std(hf_samples))  if hf_samples else 10.0

        self.TRIGGER_GATE = self.HF_MEAN + (self.HF_STD * self.TRIGGER_SIGMA)
        self.SUSTAIN_GATE = self.HF_MEAN + (self.HF_STD * self.SUSTAIN_SIGMA)

        print(
            f"[Acoustic Module] Noise profile: "
            f"μ={int(self.HF_MEAN)}  σ={int(self.HF_STD)}  "
            f"trigger={int(self.TRIGGER_GATE)}  sustain={int(self.SUSTAIN_GATE)}"
        )

    # ------------------------------------------------------------------
    # Telemetry (read by main.py → diagnostics.json)
    # ------------------------------------------------------------------

    def get_diagnostics(self) -> dict:
        return {
            "rate":         self.RATE,
            "chunk":        self.CHUNK,
            "hf_mean":      round(self.HF_MEAN, 2),
            "hf_std":       round(self.HF_STD, 2),
            "trigger_gate": round(self.TRIGGER_GATE, 2),
            "sustain_gate": round(self.SUSTAIN_GATE, 2),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_frame(self) -> bytes | None:
        """Read one 30 ms frame from the persistent stream."""
        try:
            return self._stream.read(self.CHUNK, exception_on_overflow=False)
        except Exception:
            return None

    def _hf_rms(self, frame: bytes) -> float:
        """High-pass RMS energy of a raw PCM frame."""
        arr = np.frombuffer(frame, dtype=np.int16).astype(np.float64)
        if len(arr) < 2:
            return 0.0
        return float(np.sqrt(np.mean(np.diff(arr) ** 2)))

    def _is_biological_speech(self, frame: bytes) -> bool:
        """WebRTC VAD confirmation (called only after Z-score gate fires)."""
        try:
            return self.vad.is_speech(frame, self.RATE)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Core: standby → detect → record → transcribe
    # ------------------------------------------------------------------

    def listen(self) -> tuple[str, str, str]:
        """
        Block until human speech is detected, record it, transcribe it.

        Returns
        -------
        (transcript, language_code, complexity_tier)
        e.g. ("What time is it?", "en", "micro")
        """
        print(f"\n[{Settings.ASSISTANT_NAME}] Standby — waiting for speech...")

        # Ring buffer: keeps the last PREROLL_FRAMES for look-back prepend
        ring: collections.deque = collections.deque(maxlen=self.PREROLL_FRAMES)

        # ── PHASE 1: STANDBY ──────────────────────────────────────────
        # Read tiny frames continuously. No thread, no queue — direct read
        # from the persistent stream is the fastest possible path.
        consecutive_speech = 0

        while True:
            frame = self._read_frame()
            if frame is None:
                continue

            rms = self._hf_rms(frame)
            ring.append(frame)

            if rms > self.TRIGGER_GATE and self._is_biological_speech(frame):
                consecutive_speech += 1
                if consecutive_speech >= self.TRIGGER_CONSECUTIVE:
                    # Voice confirmed — break into recording phase
                    print(f"[Speech detected (HF-RMS {int(rms)}). Recording...]")
                    break
            else:
                consecutive_speech = 0  # reset on any non-speech frame

        # ── PHASE 2: RECORD ───────────────────────────────────────────
        recording_start = time.time()

        # Prepend the ring buffer so we don't lose the utterance onset
        speech_buffer = list(ring)

        silence_counter = 0

        while True:
            frame = self._read_frame()
            if frame is None:
                continue

            speech_buffer.append(frame)

            rms = self._hf_rms(frame)
            active = (rms > self.SUSTAIN_GATE) and self._is_biological_speech(frame)

            if active:
                silence_counter = 0
            else:
                silence_counter += 1
                if silence_counter >= self.SILENCE_LIMIT:
                    break   # natural end of utterance

        recording_duration = time.time() - recording_start
        print(f"[Recording closed — {recording_duration:.2f}s captured. Transcribing...]")

        # ── PHASE 3: GUARD ────────────────────────────────────────────
        # Minimum viable audio: at least 10 frames (~300 ms of real content)
        if len(speech_buffer) < 10:
            return "None", "en", "micro"

        # ── PHASE 4: TRANSCRIBE ───────────────────────────────────────
        try:
            raw_audio = b"".join(speech_buffer)
            audio_np  = (
                np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32) / 32768.0
            )

            # Dynamic triage: shorter speech → fewer beam steps → lower latency
            if recording_duration < 1.2:
                beam_size = 1
                tier      = "micro"
            elif recording_duration < 2.8:
                beam_size = 2
                tier      = "conversational"
            else:
                beam_size = 4
                tier      = "deep"

            # ── PASS 1: LANGUAGE DETECTION ───────────────────────────
            # Detect language from the audio, then constrain to allowed
            # languages — anything outside defaults to English, preventing
            # random hallucinations (e.g. Indonesian on "hello").
            ALLOWED_LANGUAGES = {"en", "hi", "de"}

            with suppress_audio_errors():
                detected_lang, lang_probs = self.model.detect_language(audio_np)

            if detected_lang not in ALLOWED_LANGUAGES:
                # Pick the highest-scoring allowed language instead
                detected_lang = max(
                    ALLOWED_LANGUAGES,
                    key=lambda lang: lang_probs.get(lang, 0.0)
                )
                print(f"[Language constrained → {detected_lang}]")
            else:
                confidence = lang_probs.get(detected_lang, 0.0)
                print(f"[Language detected: {detected_lang} ({confidence:.0%})]")

            # ── PASS 2: TRANSCRIPTION (language now pinned) ───────────
            with suppress_audio_errors():
                segments, info = self.model.transcribe(
                    audio_np,
                    beam_size=beam_size,
                    language=detected_lang,
                    temperature=0.0,
                    vad_filter=True,
                    vad_parameters=dict(min_speech_duration_ms=250),
                )

            transcript = "".join(seg.text for seg in segments).strip()

            # ── HALLUCINATION GUARD ───────────────────────────────────
            # Whisper hallucinates by repeating tokens when audio is
            # too short or quiet. Signature: same word 3+ times in a row.
            if transcript:
                words = transcript.lower().split()
                if len(words) >= 3:
                    # Check if any single word makes up >60% of all words
                    most_common_count = max(words.count(w) for w in set(words))
                    if most_common_count / len(words) > 0.6:
                        print(f"[Hallucination rejected: '{transcript}']")
                        return "None", "en", "micro"

            if not transcript or len(transcript) <= 1:
                return "None", "en", "micro"

            print(f"--> '{transcript}'  [{info.language} / {tier}]")
            return transcript, info.language, tier

        except Exception as e:
            print(f"[Transcription error: {e}]")
            return "None", "en", "micro"

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def shutdown(self):
        """Release the persistent stream and PyAudio instance cleanly."""
        try:
            self._stream.stop_stream()
            self._stream.close()
        except Exception:
            pass
        try:
            self.pa.terminate()
        except Exception:
            pass
        print("[Acoustic Module] Stream released.")