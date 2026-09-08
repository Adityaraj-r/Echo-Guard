const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export async function analyzeAudio(file, endpoint = "/analyze") {
  console.info("[EchoGuard analysis] submitting audio", {
    endpoint,
    name: file?.name,
    type: file?.type,
    bytes: file?.size,
  });

  const formData = new FormData();
  formData.append("audio_file", file);

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    body: formData,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(getErrorMessage(data, `Analysis failed with status ${response.status}`));
  }

  console.info("[EchoGuard analysis] backend inference response", data);
  return normalizeResult(data);
}

export function toAssetUrl(path) {
  if (!path) return "";
  if (path.startsWith("/assets") && API_BASE_URL === "/api") return path;
  return path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
}

export async function fetchDetections({ page = 1, limit = 20, search = "", prediction = "" } = {}) {
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  if (search) params.set("search", search);
  if (prediction) params.set("prediction", prediction);

  const response = await fetch(`${API_BASE_URL}/detections?${params.toString()}`);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(getErrorMessage(data, `Could not load detections (${response.status})`));
  }

  return {
    ...data,
    items: (data.items ?? []).map(normalizeDetectionRecord),
  };
}

export async function deleteDetection(id) {
  const response = await fetch(`${API_BASE_URL}/detections/${id}`, { method: "DELETE" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(getErrorMessage(data, `Could not delete detection (${response.status})`));
  }
  return data;
}

function getErrorMessage(data, fallback) {
  if (typeof data.detail === "string") return data.detail;
  if (data.detail?.error && data.detail?.details) return `${data.detail.error}: ${data.detail.details}`;
  if (data.detail?.error?.message) return data.detail.error.message;
  if (data.error && data.details) return `${data.error}: ${data.details}`;
  if (data.error?.message) return data.error.message;
  if (typeof data.error === "string") return data.error;
  return fallback;
}

function normalizeResult(data) {
  const fakeProbability = normalizeProbability(data.fake_probability ?? data.analysis?.fake_probability ?? 0);
  const humanProbability = normalizeProbability(data.human_probability ?? data.analysis?.human_probability ?? 0);
  const verdict = normalizeVerdict(data.verdict, data.prediction, fakeProbability, humanProbability);
  const confidence = normalizeConfidence(data.confidence, verdict === "Fake" ? fakeProbability : humanProbability);

  return {
    filename: data.filename,
    verdict,
    label: data.analysis?.verdict ?? verdict,
    isFake: verdict === "Fake",
    isUncertain: verdict === "Uncertain" || Boolean(data.is_uncertain ?? data.analysis?.is_uncertain),
    confidenceScore: Math.round(confidence),
    fakeProbability: Math.round(fakeProbability * 100),
    humanProbability: Math.round(humanProbability * 100),
    riskLevel: data.risk_level ?? data.analysis?.risk_level ?? riskFromFakeProbability(fakeProbability),
    explanation: data.explanation ?? data.analysis?.explanation ?? "",
    anomalies: data.anomalies ?? data.analysis?.anomalies ?? [],
    forensicFeatures: data.forensic_features ?? data.analysis?.forensic_features ?? {},
    waveform: data.waveform ?? [],
    spectrogramUrl: toAssetUrl(data.spectrogram_url ?? data.spectrogram_path),
    metadata: data.metadata ?? {},
    raw: data,
  };
}

function normalizeDetectionRecord(item) {
  const fakeProbability = normalizeProbability(item.fake_probability ?? item.metadata?.fake_probability ?? 0);
  const humanProbability = normalizeProbability(item.human_probability ?? item.metadata?.human_probability ?? 0);
  const verdict = normalizeVerdict(item.verdict, item.prediction, fakeProbability, humanProbability);
  const confidence = normalizeConfidence(item.confidence, verdict === "Fake" ? fakeProbability : humanProbability);

  return {
    id: item.id,
    filename: item.filename,
    verdict,
    prediction: verdict.toLowerCase(),
    isFake: verdict === "Fake",
    isUncertain: verdict === "Uncertain" || Boolean(item.metadata?.is_uncertain),
    score: Math.round(confidence),
    confidence,
    time: item.uploaded_at ? new Date(item.uploaded_at).toLocaleString() : "Unknown",
    waveformImageUrl: toAssetUrl(item.waveform_image),
    spectrogramUrl: toAssetUrl(item.spectrogram_image),
    duration: item.duration,
    sampleRate: item.sample_rate,
    isLiveRecording: item.is_live_recording,
    raw: item,
  };
}

function normalizeVerdict(verdict, prediction, fakeProbability, humanProbability) {
  const value = String(verdict ?? prediction ?? "").toLowerCase();
  if (value.includes("uncertain")) return "Uncertain";
  if (value.includes("fake") || value.includes("synthetic")) return "Fake";
  if (value.includes("human") || value.includes("real") || value.includes("authentic")) return "Human";
  if (fakeProbability >= 0.35 && fakeProbability < 0.65) return "Uncertain";
  return fakeProbability > humanProbability ? "Fake" : "Human";
}

function normalizeProbability(value) {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number)) return 0;
  return number > 1 ? Math.min(number / 100, 1) : Math.max(number, 0);
}

function normalizeConfidence(value, probabilityFallback) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) return probabilityFallback * 100;
  return number > 1 ? number : number * 100;
}

function riskFromFakeProbability(fakeProbability) {
  if (fakeProbability >= 0.65) return "High";
  if (fakeProbability >= 0.35) return "Medium";
  return "Low";
}
