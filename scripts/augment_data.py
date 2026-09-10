import os
import glob
from backend.preprocessing.audio_processor import generate_spectrogram

# Create a folder for the output images
os.makedirs("elevenlabs_specs", exist_ok=True)

# Find all audio files in the raw folder
audio_files = glob.glob("elevenlabs_raw/*.wav") + glob.glob("elevenlabs_raw/*.mp3")

print(f"⚙️ Found {len(audio_files)} ElevenLabs files. Converting...")

for i, audio_path in enumerate(audio_files):
    output_path = f"elevenlabs_specs/elevenlabs_fake_{i}.png"
    generate_spectrogram(audio_path, output_path)
    print(f"   Converted {i+1}/{len(audio_files)}")

print("✅ All ElevenLabs deepfakes converted to spectrograms!")