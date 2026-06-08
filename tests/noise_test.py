# test_noise.py
import pyaudio
import numpy as np
import time

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024

print("[Diagnostic Mode] Initializing hardware stream layer...")
p = pyaudio.PyAudio()
stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

print("\n>>> RECORDING STARTED (Keep quiet, let the fans run full speed) <<<")
print("Sampling room profile for 5 seconds...")

rms_values = []
peak_frequencies = []
start_time = time.time()

while time.time() - start_time < 5.0:
    try:
        data = stream.read(CHUNK, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float64)
        
        if len(audio_data) > 0:
            # 1. Calculate raw volume metrics (RMS)
            rms = np.sqrt(np.mean(audio_data**2))
            rms_values.append(rms)
            
            # 2. Extract frequency data using FFT
            fft_data = np.abs(np.fft.rfft(audio_data))
            frequencies = np.fft.rfftfreq(len(audio_data), d=1.0/RATE)
            peak_freq = frequencies[np.argmax(fft_data)]
            peak_frequencies.append(peak_freq)
    except Exception as e:
        print(f"Read error: {e}")

stream.stop_stream()
stream.close()
p.terminate()

print("\n========================================")
print(" >> DIAGNOSTIC MATRIX PROFILE RESULTS <<")
print("========================================")
print(f"Maximum Volume Peak (RMS): {int(np.max(rms_values))}")
print(f"Average Volume Level (RMS): {int(np.mean(rms_values))}")
print(f"Dominant Fan Noise Frequency: {int(np.median(peak_frequencies))} Hz")
print("========================================\n")