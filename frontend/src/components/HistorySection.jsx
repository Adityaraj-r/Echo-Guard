import { RefreshCw, Trash2 } from "lucide-react";

export default function HistorySection({ history, isLoading = false, error = "", onRefresh, onDelete }) {
  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="section-title">Detection History</h2>
          <p className="section-copy">MongoDB-backed forensic records, newest first.</p>
        </div>
        <button className="secondary-button" onClick={onRefresh} disabled={isLoading}>
          <RefreshCw className={isLoading ? "animate-spin" : ""} size={16} />
          Refresh
        </button>
      </div>

      {error && <p className="mt-3 rounded-lg border border-amber-300/30 bg-amber-400/10 p-3 text-sm text-amber-100">{error}</p>}

      <div className="mt-4 space-y-3">
        {isLoading && history.length === 0 ? (
          <p className="text-sm text-slate-400">Loading detections from MongoDB...</p>
        ) : history.length === 0 ? (
          <p className="text-sm text-slate-400">No stored detections yet. Analyze audio to create the first record.</p>
        ) : (
          history.map((item) => <HistoryRow key={item.id} item={item} onDelete={() => onDelete?.(item.id)} />)
        )}
      </div>
    </div>
  );
}

function HistoryRow({ item, onDelete }) {
  return (
    <div className="grid gap-3 rounded-lg border border-white/10 bg-black/25 p-3 md:grid-cols-[96px_96px_minmax(0,1fr)_auto] md:items-center">
      <Thumb src={item.waveformImageUrl} label="Waveform" />
      <Thumb src={item.spectrogramUrl} label="Spectrogram" />

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate font-medium text-slate-100">{item.filename}</p>
          <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${item.isFake ? "bg-rose-400/15 text-rose-200" : "bg-emerald-400/15 text-emerald-200"}`}>
            {item.isFake ? "FAKE" : "HUMAN"}
          </span>
          {item.isLiveRecording && <span className="rounded-full bg-cyan-300/10 px-2 py-0.5 text-xs font-semibold text-cyan-100">LIVE</span>}
        </div>
        <p className="mt-1 text-sm text-slate-500">{item.time}</p>
        <p className="mt-1 text-sm text-slate-400">
          Confidence {item.score}% {item.duration ? `- ${item.duration}s` : ""} {item.sampleRate ? `- ${item.sampleRate} Hz` : ""}
        </p>
      </div>

      <button className="secondary-button justify-self-start text-rose-100 md:justify-self-end" onClick={onDelete}>
        <Trash2 size={16} />
        Delete
      </button>
    </div>
  );
}

function Thumb({ src, label }) {
  return (
    <div className="h-20 overflow-hidden rounded-md border border-white/10 bg-slate-950/70">
      {src ? (
        <img className="h-full w-full object-cover" src={src} alt={label} />
      ) : (
        <div className="grid h-full place-items-center text-xs text-slate-500">{label}</div>
      )}
    </div>
  );
}
