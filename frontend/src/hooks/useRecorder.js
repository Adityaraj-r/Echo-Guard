import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getMicrophoneSupportError,
  getRecorderErrorMessage,
  getSupportedRecordingMimeType,
} from "../utils/browser.js";
import { convertRecordingBlobToWavFile } from "../utils/wav.js";

export function useRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [isPreparing, setIsPreparing] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [liveWaveform, setLiveWaveform] = useState([]);
  const [recordedFile, setRecordedFile] = useState(null);
  const [recordedUrl, setRecordedUrl] = useState("");
  const [error, setError] = useState("");
  const supportError = useMemo(() => getMicrophoneSupportError(), []);

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const audioContextRef = useRef(null);
  const animationRef = useRef(0);
  const startedAtRef = useRef(0);
  const stopPromiseRef = useRef(null);

  const clearRecording = useCallback(() => {
    if (recordedUrl) URL.revokeObjectURL(recordedUrl);
    setRecordedFile(null);
    setRecordedUrl("");
  }, [recordedUrl]);

  const stopVisualizer = useCallback(() => {
    cancelAnimationFrame(animationRef.current);
    animationRef.current = 0;
    audioContextRef.current?.close();
    audioContextRef.current = null;
  }, []);

  const stopTracks = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const startVisualizer = useCallback((stream) => {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;

    const context = new AudioContextClass();
    const analyser = context.createAnalyser();
    analyser.fftSize = 1024;
    context.createMediaStreamSource(stream).connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);
    audioContextRef.current = context;

    const tick = () => {
      analyser.getByteTimeDomainData(data);
      const samples = Array.from(data)
        .filter((_, index) => index % 8 === 0)
        .map((value) => Math.abs((value - 128) / 128));
      setLiveWaveform(samples);
      setElapsedMs(Date.now() - startedAtRef.current);
      animationRef.current = requestAnimationFrame(tick);
    };
    tick();
  }, []);

  const startRecording = useCallback(async () => {
    setError("");

    if (supportError) {
      setError(supportError);
      return { ok: false, error: supportError };
    }

    clearRecording();
    setIsPreparing(true);
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      const mimeType = getSupportedRecordingMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onerror = (event) => {
        setError(getRecorderErrorMessage(event.error));
      };

      mediaRecorderRef.current = recorder;
      streamRef.current = stream;
      startedAtRef.current = Date.now();
      setElapsedMs(0);
      setLiveWaveform([]);

      // Collect small chunks so mobile browsers flush data reliably on stop.
      recorder.start(250);
      setIsRecording(true);
      startVisualizer(stream);
      return { ok: true };
    } catch (exception) {
      const message = getRecorderErrorMessage(exception);
      setError(message);
      stopTracks();
      return { ok: false, error: message };
    } finally {
      setIsPreparing(false);
    }
  }, [clearRecording, startVisualizer, stopTracks, supportError]);

  const stopRecording = useCallback(
    () => {
      if (stopPromiseRef.current) return stopPromiseRef.current;

      stopPromiseRef.current = new Promise((resolve) => {
        const recorder = mediaRecorderRef.current;
        if (!recorder || recorder.state === "inactive") {
          stopPromiseRef.current = null;
          resolve(null);
          return;
        }

        recorder.onstop = async () => {
          const mimeType = recorder.mimeType || getSupportedRecordingMimeType() || "audio/webm";
          const blob = new Blob(chunksRef.current, { type: mimeType });
          const elapsed = Date.now() - startedAtRef.current;

          setIsRecording(false);
          setIsPreparing(true);
          stopVisualizer();
          stopTracks();

          try {
            if (!blob.size) {
              throw new Error("No microphone audio was captured.");
            }

            console.info("[EchoGuard recorder] captured MediaRecorder blob", {
              mimeType,
              bytes: blob.size,
              chunks: chunksRef.current.length,
              elapsedMs: elapsed,
            });

            const file = await convertRecordingBlobToWavFile(blob, `live-recording-${Date.now()}.wav`);
            const url = URL.createObjectURL(file);
            setRecordedFile(file);
            setRecordedUrl(url);
            setError("");
            resolve(file);
          } catch (exception) {
            const message = exception?.message || "Unable to prepare microphone recording for analysis.";
            console.error("[EchoGuard recorder] WAV finalization failed", exception);
            setRecordedFile(null);
            setRecordedUrl("");
            setError(message);
            resolve(null);
          } finally {
            setIsPreparing(false);
            stopPromiseRef.current = null;
          }
        };

        recorder.requestData?.();
        recorder.stop();
      });

      return stopPromiseRef.current;
    },
    [stopTracks, stopVisualizer],
  );

  useEffect(
    () => () => {
      stopVisualizer();
      stopTracks();
      if (recordedUrl) URL.revokeObjectURL(recordedUrl);
    },
    [recordedUrl, stopTracks, stopVisualizer],
  );

  return {
    elapsedMs,
    error,
    isPreparing,
    isRecording,
    liveWaveform,
    recordedFile,
    recordedUrl,
    supportError,
    clearRecording,
    startRecording,
    stopRecording,
  };
}
