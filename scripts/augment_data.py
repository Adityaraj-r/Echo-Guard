import os
import glob
import sys

if "--legacy-mel" in sys.argv:
    from backend.preprocessing.legacy_spectrogram import generate_legacy_mel_spectrogram as generate_spectrogram

    output_directory = "elevenlabs_specs_legacy_mel"
else:
    from backend.preprocessing.audio_processor import generate_spectrogram

    output_directory = "elevenlabs_specs"

# Create a folder for the output images
os.makedirs(output_directory, exist_ok=True)

# Find all audio files in the raw folder
audio_files = glob.glob("elevenlabs_raw/*.wav") + glob.glob("elevenlabs_raw/*.mp3")

print(f"⚙️ Found {len(audio_files)} ElevenLabs files. Converting...")

for i, audio_path in enumerate(audio_files):
    output_path = os.path.join(output_directory, f"elevenlabs_fake_{i}.png")
    generate_spectrogram(audio_path, output_path)
    print(f"   Converted {i+1}/{len(audio_files)}")

print("✅ All ElevenLabs deepfakes converted to spectrograms!")
