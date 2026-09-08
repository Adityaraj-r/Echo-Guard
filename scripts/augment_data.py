import os
import glob
from backend.preprocessing.audio_processor import generate_spectrogram

# Create a folder for the output images
os.makedirs("elevenlabs_specs", exist_ok=True)

# Find all audio files in the raw folder
audio_files = glob.glob("elevenlabs_raw/*.wav") + glob.glob("elevenlabs_raw/*.mp3")

print(f"⚙️ Found {len(audio_files)} ElevenLabs files. Converting...")

