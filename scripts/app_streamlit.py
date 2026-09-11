import streamlit as st
import requests
import time

# UI Configuration
st.set_page_config(page_title="EchoGuard", page_icon="🛡️", layout="centered")

st.title("🛡️ EchoGuard: Vishing Defense")
st.markdown("Upload a suspicious voice clip to analyze its acoustic fingerprint for AI synthesis.")

# File Uploader
uploaded_file = st.file_uploader("Upload Audio (.wav)", type=["wav"])
if uploaded_file is not None:
    # Play the audio in the UI
    st.audio(uploaded_file, format='audio/wav')

    if st.button("Scan Audio for Deepfakes"):
        # Cool loading animation for the presentation
        progress_text = "Extracting Mel-Spectrogram & analyzing frequencies..."
        my_bar = st.progress(0, text=progress_text)
        for percent_complete in range(100):
            time.sleep(0.01)
            my_bar.progress(percent_complete + 1, text=progress_text)
        
        # Send the file to your FastAPI backend
        files = {"audio_file": (uploaded_file.name, uploaded_file, "audio/wav")}
        
        try:
            response = requests.post("http://127.0.0.1:8000/analyze", files=files)
            
            if response.status_code == 200:
                data = response.json()
                result = data["analysis"]
                
                st.divider()
                st.subheader("Analysis Results")
                
                # Dynamic UI colors based on the AI verdict
                if result["ui_color"] == "red":
                    st.error(f"🚨 CRITICAL ALERT: {result['verdict']}")
                    st.metric(label="Synthetic Probability Score", value=f"{result['threat_score']*100:.1f}%")
                else:
                    st.success(f"✅ PASSED: {result['verdict']}")
                    st.metric(label="Authenticity Score", value=f"{(1.0 - result['threat_score'])*100:.1f}%")
                
                # Display the Spectrogram Image the backend generated
                st.markdown("### Acoustic Frequency Map")
                st.image(data["spectrogram_path"], caption="Mel-Spectrogram (Magma Scale)", use_container_width=True)
                
            else:
                st.error(f"Backend Error: {response.status_code}")
                
       