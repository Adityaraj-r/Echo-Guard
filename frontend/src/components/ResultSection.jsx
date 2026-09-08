import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import { formatBytes, formatDuration } from "../utils/format.js";
import WaveformPanel from "./WaveformPanel.jsx";

export default function ResultSection({ result, isAnalyzing, progress, audioUrl, error }) {
  const tone = result?.isUncertain ? "text-amber-200" : result?.isFake ? "text-rose-300" : "text-emerald-300";

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="section-title">Analysis Result</h2>
          <p className="section-copy">Prediction, confidence, waveform, spectrogram, and extracted media evidence.</p>
        </div>
        {isAnalyzing ? <Loader2 className="animate-spin text-cyan-300" /> : result?.isFake || result?.isUncertain ? <AlertTriangle className={tone} /> : result ? <CheckCircle2 className="text-emerald-300" /> : null}
      </div>

      <AnimatePresence mode="wait">
        {isAnalyzing ? (
          <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <p className="text-lg font-semibold text-slate-50">Running forensic pipeline</p>
            <p className="mt-1 text-sm text-slate-400">Converting audio, extracting features, generating visuals, and scoring the model.</p>
            <div className="mt-5 h-3 overflow-hidden rounded-full bg-white/10">
              <motion.div className="h-full rounded-full bg-cyan-300" animate={{ width: `${progress}%` }} />
            </div>
          </motion.div>
        ) : result ? (
          <motion.div key="result" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <Metric label="Verdict" value={result.verdict} className={tone} />
              <Metric label="Confidence" value={`${result.confidenceScore}%`} />
              <Metric label="Risk Level" value={result.riskLevel} className={tone} />
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Probability label="Fake probability" value={result.fakeProbability} tone="bg-rose-400" />
              <Probability label="Human probability" value={result.humanProbability} tone="bg-emerald-400" />
            </div>

            {result.isUncertain && (
              <div className="rounded-lg border border-amber-300/30 bg-amber-400/10 p-4 text-amber-100">
                <p className="font-semibold">Uncertain prediction</p>
                <p className="mt-1 text-sm text-amber-100/80">{result.explanation || "Score is inside the 35-65% uncertainty band."}</p>
              </div>
            )}

            {(result.anomalies?.length > 0 || result.explanation) && (
              <div className="rounded-lg border border-white/10 bg-black/25 p-4">
                <p className="font-semibold text-slate-50">Forensic Interpretation</p>
                {result.explanation && <p className="mt-2 text-sm text-slate-300">{result.explanation}</p>}
                {result.anomalies?.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {result.anomalies.map((item) => (
                      <span key={item} className="rounded-full bg-cyan-300/10 px-3 py-1 text-xs font-semibold text-cyan-100">
                        {item}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {audioUrl && <audio className="w-full" controls src={audioUrl} />}
            <WaveformPanel audioUrl={audioUrl} waveform={result.waveform} />

            {result.spectrogramUrl && (
              <div className="rounded-lg border border-white/10 bg-black/25 p-3">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <p className="font-semibold text-slate-50">Spectrogram Heatmap</p>
                  <span className="truncate text-xs text-slate-400">{result.filename}</span>
                </div>
                <img className="max-h-96 w-full rounded-md object-contain" src={result.spectrogramUrl} alt="Frequency heatmap spectrogram" />
              </div>
            )}

            <Metadata metadata={result.metadata} />
          </motion.div>
        ) : (
          <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid min-h-64 place-items-center rounded-lg border border-dashed border-white/15 bg-black/20 p-8 text-center">
            <div>
              <p className="text-lg font-semibold text-slate-50">Awaiting evidence</p>
              <p className="mt-2 max-w-sm text-sm text-slate-400">Upload or record audio to produce a full forensic authenticity report.</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {error && <p className="rounded-lg border border-amber-300/30 bg-amber-400/10 p-3 text-sm text-amber-100">{error}</p>}
    </div>
  );
}

function Metric({ label, value, className = "text-slate-50" }) {
  return (
    <div className="rounded-lg border border-white/10 bg-black/25 p-4">
      <p className="text-sm text-slate-400">{label}</p>
      <p className={`mt-2 text-2xl font-semibold capitalize ${className}`}>{value}</p>
    </div>
  );
}

function Probability({ label, value, tone }) {
  return (
    <div className="rounded-lg border border-white/10 bg-black/25 p-4">
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-300">{label}</span>
        <span className="font-semibold text-slate-50">{value}%</span>
      </div>
      <div className="mt-3 h-3 overflow-hidden rounded-full bg-white/10">
        <motion.div className={`h-full rounded-full ${tone}`} initial={{ width: 0 }} animate={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function Metadata({ metadata }) {
  const items = [
    ["Duration", formatDuration(metadata.duration)],
    ["Sample rate", metadata.sample_rate ? `${metadata.sample_rate} Hz` : "Unknown"],
    ["Bitrate", metadata.bitrate ? `${metadata.bitrate} kbps` : "Unknown"],
    ["Channels", metadata.channels ?? "Unknown"],
    ["Codec", metadata.codec ?? "Unknown"],
    ["File size", formatBytes(metadata.file_size)],
  ];

  return (
    <div>
      <p className="mb-3 font-semibold text-slate-50">Audio Metadata</p>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {items.map(([label, value]) => (
          <div key={label} className="rounded-lg border border-white/10 bg-black/25 p-3">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
            <p className="mt-1 font-medium text-slate-100">{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
