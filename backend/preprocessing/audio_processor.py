import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import os
from scipy import signal
from backend.preprocessing.audio_io import load_audio_fast

def generate_spectrogram(audio_path, output_image_path, duration=5.0):
    """
    Ingests an audio file and exports a perfectly borderless Mel-Spectrogram image.
    Forces all audio to a strict duration to guarantee uniform CNN input dimensions.
    """
    try:
        # 1. Load and Standardize the Audio
        # sr=22050 is the standard sample rate. We strictly enforce a 5-second duration.
        print(f"Loading audio: {audio_path}...")
        y, sr = load_audio_fast(audio_path, 22050, mono=True)
        y = y[: int(sr * duration)]
        
        # 2. Array Padding (The Critical Step)
        # If the scammer's audio is only 3 seconds long, the resulting image would be too narrow.
        # We pad the numpy array with zeros (absolute silence) to reach exactly 5 seconds.
        target_length = int(sr * duration)
        if len(y) < target_length:
            y = np.pad(y, (0, target_length - len(y)), mode='constant')

        # 3. Fast Fourier Transform (Time Domain -> Frequency Domain)
        # n_fft defines the window size, hop_length is the stride of the sliding window.
        print("Calculating spectrogram matrix...")
        _, _, spectrum = signal.spectrogram(
            y,
            fs=sr,
            window="hann",
            nperseg=1024,
            noverlap=768,
            scaling="spectrum",
            mode="magnitude",
        )
        spectrum_db = 20 * np.log10(spectrum + 1e-8)

        # 4. Image Generation and Export
        # We must strip all axes, labels, and white borders. The AI should only see the data pixels.
        plt.figure(figsize=(5, 5), dpi=100) # Forces a strict 500x500 pixel output
        plt.axis('off')
        plt.margins(0,0)
        plt.gca().xaxis.set_major_locator(plt.NullLocator())
        plt.gca().yaxis.set_major_locator(plt.NullLocator())
        
        plt.imshow(spectrum_db, aspect="auto", origin="lower", cmap="magma")
        
        # Save the raw tensor visually to the disk
        plt.savefig(output_image_path, bbox_inches='tight', pad_inches=0, transparent=True)
        plt.close()
        
        print(f"Success! Spectrogram saved cleanly to: {output_image_path}")
        return output_image_path

    except Exception as e:
        print(f"Pipeline failure - error processing audio: {e}")
        return None

# --- Local Testing Block ---
if __name__ == "__main__":
    # Create a directory to hold our test visuals
    os.makedirs("test_data", exist_ok=True)
    
    # NOTE: You need to place a temporary .wav or .mp3 file in your folder named 'test_voice.wav'
    # Uncomment the lines below to run the test once you have the audio file ready.
    
    input_audio = "test_voice.wav" 
    output_image = "test_data/spectrogram_output.png"
    generate_spectrogram(input_audio, output_image)
