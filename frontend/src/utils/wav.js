const TARGET_SAMPLE_RATE = 16000;
const TARGET_CHANNELS = 1;
const MIN_RECORDING_BYTES = 1024;
const MIN_DURATION_SECONDS = 0.25;

export async function convertRecordingBlobToWavFile(blob, filename = `live-recording-${Date.now()}.wav`) {
  validateRecordingBlob(blob);

  const sourceBuffer = await blob.arrayBuffer();
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    throw new Error("This browser cannot decode microphone audio for WAV export.");
  }

  const audioContext = new AudioContextClass();
  let decodedBuffer;
  try {
    decodedBuffer = await audioContext.decodeAudioData(sourceBuffer.slice(0));
  } finally {
    await audioContext.close?.();
  }

  validateDecodedAudio(decodedBuffer);

  const renderedBuffer = await renderMono16k(decodedBuffer);
  const samples = renderedBuffer.getChannelData(0);
  const normalizedSamples = normalizeFloat32(samples);
  const wavBlob = encodePcm16Wav(normalizedSamples, TARGET_SAMPLE_RATE);
  const duration = normalizedSamples.length / TARGET_SAMPLE_RATE;

  validateWavBlob(wavBlob, duration);

  const file = new File([wavBlob], filename.replace(/\.[^.]+$/, ".wav"), {
    type: "audio/wav",
    lastModified: Date.now(),
  });

  console.info("[EchoGuard recorder] WAV export complete", {
    sourceType: blob.type || "unknown",
    sourceBytes: blob.size,
    durationSeconds: Number(duration.toFixed(3)),
    sourceSampleRate: decodedBuffer.sampleRate,
    sourceChannels: decodedBuffer.numberOfChannels,
    targetSampleRate: TARGET_SAMPLE_RATE,
    targetChannels: TARGET_CHANNELS,
    wavBytes: file.size,
    normalization: summarizeNormalization(samples, normalizedSamples),
  });

  return file;
}

function validateRecordingBlob(blob) {
  if (!(blob instanceof Blob)) {
    throw new Error("No microphone audio was captured.");
  }
  if (blob.size < MIN_RECORDING_BYTES) {
    throw new Error("Recording is empty or too short to analyze. Please record a longer sample.");
  }
}

function validateDecodedAudio(audioBuffer) {
  if (!audioBuffer || audioBuffer.length === 0 || audioBuffer.duration < MIN_DURATION_SECONDS) {
    throw new Error("Recording is too short to analyze. Please record at least one second of speech.");
  }
  if (audioBuffer.numberOfChannels < 1) {
    throw new Error("Recording has no audio channels.");
  }
}

async function renderMono16k(decodedBuffer) {
  const frameCount = Math.max(1, Math.ceil(decodedBuffer.duration * TARGET_SAMPLE_RATE));
  const OfflineAudioContextClass = window.OfflineAudioContext || window.webkitOfflineAudioContext;
  if (!OfflineAudioContextClass) {
    throw new Error("This browser cannot resample microphone audio for analysis.");
  }

  const offlineContext = new OfflineAudioContextClass(TARGET_CHANNELS, frameCount, TARGET_SAMPLE_RATE);
  const source = offlineContext.createBufferSource();
  source.buffer = decodedBuffer;

  const merger = offlineContext.createGain();
  source.connect(merger);
  merger.connect(offlineContext.destination);
  source.start(0);

  return offlineContext.startRendering();
}

function normalizeFloat32(samples) {
  const normalized = new Float32Array(samples.length);
  let peak = 0;

  for (let index = 0; index < samples.length; index += 1) {
    const value = Number.isFinite(samples[index]) ? samples[index] : 0;
    peak = Math.max(peak, Math.abs(value));
    normalized[index] = value;
  }

  if (peak > 0) {
    const gain = Math.min(1 / peak, 8);
    for (let index = 0; index < normalized.length; index += 1) {
      normalized[index] = Math.max(-1, Math.min(1, normalized[index] * gain));
    }
  }

  return normalized;
}

function encodePcm16Wav(samples, sampleRate) {
  const bytesPerSample = 2;
  const dataSize = samples.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  writeAscii(view, 0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeAscii(view, 8, "WAVE");
  writeAscii(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, TARGET_CHANNELS, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * TARGET_CHANNELS * bytesPerSample, true);
  view.setUint16(32, TARGET_CHANNELS * bytesPerSample, true);
  view.setUint16(34, 16, true);
  writeAscii(view, 36, "data");
  view.setUint32(40, dataSize, true);

  let offset = 44;
  for (let index = 0; index < samples.length; index += 1, offset += 2) {
    const sample = Math.max(-1, Math.min(1, samples[index]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }

  return new Blob([view], { type: "audio/wav" });
}

function validateWavBlob(blob, duration) {
  if (blob.size <= 44 || duration < MIN_DURATION_SECONDS) {
    throw new Error("Normalized recording is empty or corrupted.");
  }
}

function summarizeNormalization(before, after) {
  return {
    inputPeak: Number(getPeak(before).toFixed(6)),
    outputPeak: Number(getPeak(after).toFixed(6)),
    normalized: getPeak(before) > 0,
  };
}

function getPeak(samples) {
  let peak = 0;
  for (let index = 0; index < samples.length; index += 1) {
    peak = Math.max(peak, Math.abs(samples[index] || 0));
  }
  return peak;
}

function writeAscii(view, offset, text) {
  for (let index = 0; index < text.length; index += 1) {
    view.setUint8(offset + index, text.charCodeAt(index));
  }
}
