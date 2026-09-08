import { motion } from "framer-motion";
import { AlertTriangle, Loader2, Mic, RotateCcw, Send, Square } from "lucide-react";
import { formatTimer } from "../utils/format.js";
import WaveformPanel from "./WaveformPanel.jsx";

export default function RecorderSection({ recorder, onRecorded, isAnalyzing = false, onToast }) {
  async function toggleRecording() {
    if (recorder.isRecording) {
      const file = await recorder.stopRecording();
      if (file) {
        onToast?.("Recording captured. Sending audio to EchoGuard.", "info");
        onRecorded(file);
      }
      return;
    }

    const result = await recorder.startRecording();
    if (result.ok) {
      onToast?.("Microphone recording started.", "info");
    } else if (result.error) {
      onToast?.(result.error, "error");
    }
  }

  function submitLastRecording() {
    if (!recorder.recordedFile) return;
    onToast?.("Submitting saved recording for analysis.", "info");
    onRecorded(recorder.recordedFile);
  }

  const disabled = recorder.isPreparing || isAnalyzing;

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="section-title">Live Microphone</h2>
          <p className="section-copy">Record a caller sample and submit it directly into the same forensic pipeline.</p>
        </div>
        <div className="text-left sm:text-right">
          <p className="font-mono text-2xl font-semibold text-slate-50">{formatTimer(recorder.elapsedMs)}</p>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Timer</p>
        </div>
      </div>

      <button
        className={`mic-button ${recorder.isRecording ? "mic-button-recording" : ""}`}
        onClick={toggleRecording}
        disabled={disabled}
      >
        <motion.span
          animate={recorder.isRecording ? { scale: [1, 1.14, 1] } : { scale: 1 }}
          transition={{ repeat: recorder.isRecording ? Infinity : 0, duration: 1.1 }}
          className="grid h-8 w-8 place-items-center rounded-full bg-white/10"
        >
          {recorder.isPreparing ? <Loader2 className="animate-spin" size={22} /> : recorder.isRecording ? <Square size={22} /> : <Mic size={22} />}
        </motion.span>
        {recorder.isPreparing ? "Requesting permission" : recorder.isRecording ? "Stop recording" : "Start microphone scan"}
      </button>

      <WaveformPanel liveWaveform={recorder.liveWaveform} />

      {recorder.recordedUrl && (
        <div className="space-y-3 rounded-lg border border-white/10 bg-black/25 p-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="font-semibold text-slate-100">Recording preview</p>
            <div className="flex gap-2">
              <button className="secondary-button" onClick={recorder.clearRecording} disabled={isAnalyzing}>
                <RotateCcw size={16} />
                Reset
              </button>
              <button className="secondary-button" onClick={submitLastRecording} disabled={isAnalyzing}>
                <Send size={16} />
                Analyze
              </button>
            </div>
          </div>
          <audio className="w-full" controls src={recorder.recordedUrl} />
        </div>
      )}

      {(recorder.error || recorder.supportError) && (
        <div className="flex gap-3 rounded-lg border border-rose-400/30 bg-rose-500/10 p-3 text-sm text-rose-100">
          <AlertTriangle className="mt-0.5 shrink-0" size={18} />
          <div>
            <p>{recorder.error || recorder.supportError}</p>
            <p className="mt-1 text-rose-100/70">Use Chrome, Edge, or Firefox on localhost or HTTPS, then allow microphone permission.</p>
          </div>
        </div>
      )}
    </div>
  );
}
