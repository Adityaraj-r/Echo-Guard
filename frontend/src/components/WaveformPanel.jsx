import { useEffect, useMemo, useRef } from "react";
import WaveSurfer from "wavesurfer.js";

export default function WaveformPanel({ audioUrl, waveform = [], liveWaveform = [] }) {
  const containerRef = useRef(null);
  const wavesurferRef = useRef(null);
  const displayWaveform = liveWaveform.length ? liveWaveform : waveform;

  useEffect(() => {
    if (!containerRef.current || !audioUrl) return undefined;
    wavesurferRef.current?.destroy();
    wavesurferRef.current = WaveSurfer.create({
      container: containerRef.current,
      waveColor: "#38bdf8",
      progressColor: "#2dd4bf",
      cursorColor: "#f8fafc",
      height: 112,
      barWidth: 2,
      barGap: 2,
      normalize: true,
      responsive: true,
    });
    wavesurferRef.current.load(audioUrl);
    return () => wavesurferRef.current?.destroy();
  }, [audioUrl]);

  const bars = useMemo(() => displayWaveform.slice(0, 96), [displayWaveform]);

  return (
    <div className="min-h-36 rounded-lg border border-white/10 bg-black/25 p-4">
      {audioUrl ? (
        <div ref={containerRef} />
      ) : (
        <div className="flex h-28 items-center gap-1 overflow-hidden">
          {(bars.length ? bars : Array.from({ length: 64 }, () => 0.08)).map((value, index) => (
            <span
              key={`${index}-${value}`}
              className="flex-1 rounded-full bg-cyan-300/80 transition-all duration-150"
              style={{ height: `${Math.max(8, value * 96)}px` }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
