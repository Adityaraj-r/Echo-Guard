import { motion } from "framer-motion";
import { useCallback, useMemo, useState } from "react";
import GlassCard from "../components/GlassCard.jsx";
import HistorySection from "../components/HistorySection.jsx";
import RecorderSection from "../components/RecorderSection.jsx";
import ResultSection from "../components/ResultSection.jsx";
import ToastStack from "../components/ToastStack.jsx";
import UploadSection from "../components/UploadSection.jsx";
import { useDetections } from "../hooks/useDetections.js";
import { useRecorder } from "../hooks/useRecorder.js";
import DashboardLayout from "../layouts/DashboardLayout.jsx";
import { analyzeAudio } from "../services/api.js";
import { createId } from "../utils/ids.js";

export default function DashboardPage() {
  const [activeSection, setActiveSection] = useState("upload");
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [toasts, setToasts] = useState([]);
  const recorder = useRecorder();
  const audioUrl = useMemo(() => (file ? URL.createObjectURL(file) : ""), [file]);

  const addToast = useCallback((message, type = "info") => {
    const id = createId("toast");
    setToasts((items) => [...items, { id, message, type }].slice(-4));
    window.setTimeout(() => {
      setToasts((items) => items.filter((item) => item.id !== id));
    }, 5200);
  }, []);

  const handleHistoryError = useCallback((message) => addToast(message, "error"), [addToast]);
  const { history, historyError, isLoadingHistory, loadHistory, removeDetection } = useDetections(handleHistoryError);

  async function runAnalysis(nextFile, endpoint = "/analyze") {
    setFile(nextFile);
    setError("");
    setIsAnalyzing(true);
    setProgress(12);
    setActiveSection("analysis");
    const timer = window.setInterval(() => setProgress((value) => Math.min(value + 8, 88)), 240);

    try {
      const nextResult = await analyzeAudio(nextFile, endpoint);
      setResult(nextResult);
      addToast("Analysis complete. Forensic report is ready.", "info");
      loadHistory();
      setProgress(100);
    } catch (exception) {
      const message = exception.message || "Unable to analyze this audio.";
      setError(message);
      addToast(message, "error");
      setProgress(0);
    } finally {
      window.clearInterval(timer);
      setIsAnalyzing(false);
    }
  }

  return (
    <DashboardLayout activeSection={activeSection} setActiveSection={setActiveSection} status={isAnalyzing ? "Analyzing" : "Ready"}>
      <ToastStack toasts={toasts} onDismiss={(id) => setToasts((items) => items.filter((item) => item.id !== id))} />
      <div className="px-4 py-6 md:px-8">
        <motion.section
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 grid gap-4 md:grid-cols-3"
        >
          <Kpi label="Supported formats" value="10+" />
          <Kpi label="Live analysis" value="Mic ready" />
          <Kpi label="Pipeline" value="FFmpeg + CNN" />
        </motion.section>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(420px,1.05fr)]">
          <div className="space-y-6">
            <GlassCard>
              <div id="upload">
                <h2 className="section-title">Upload Audio</h2>
                <p className="section-copy">Submit suspicious audio evidence for normalized WAV conversion and AI scoring.</p>
                <UploadSection file={file} onFile={(selected) => runAnalysis(selected)} />
              </div>
            </GlassCard>

            <GlassCard id="record">
              <RecorderSection
                recorder={recorder}
                isAnalyzing={isAnalyzing}
                onToast={addToast}
                onRecorded={(recordedFile) => runAnalysis(recordedFile)}
              />
            </GlassCard>
          </div>

          <div className="space-y-6">
            <GlassCard id="analysis">
              <ResultSection result={result} isAnalyzing={isAnalyzing} progress={progress} audioUrl={audioUrl} error={error} />
            </GlassCard>

            <GlassCard id="history">
              <HistorySection
                history={history}
                isLoading={isLoadingHistory}
                error={historyError}
                onRefresh={loadHistory}
                onDelete={removeDetection}
              />
            </GlassCard>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}

function Kpi({ label, value }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.06] p-4 backdrop-blur-xl">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-semibold text-slate-50">{value}</p>
    </div>
  );
}
