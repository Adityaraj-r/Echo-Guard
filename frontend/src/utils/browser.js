export function isLocalhost(hostname = window.location.hostname) {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
}

export function isSecureMicContext() {
  return window.isSecureContext || isLocalhost();
}

export function getSupportedRecordingMimeType() {
  if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) {
    return "";
  }

  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/ogg",
    "audio/mp4",
  ];

  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

export function getMicrophoneSupportError() {
  if (typeof window === "undefined" || typeof navigator === "undefined") {
    return "Microphone recording is not available in this browser context.";
  }

  if (!isSecureMicContext()) {
    return "Microphone access is only available on HTTPS or localhost. For a LAN IP address, run the HTTPS dev server.";
  }

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    return "This browser does not support secure microphone capture. Try the latest Chrome, Edge, or Firefox.";
  }

  if (typeof MediaRecorder === "undefined") {
    return "This browser can access the microphone but does not support MediaRecorder.";
  }

  return "";
}

export function getRecorderErrorMessage(error) {
  switch (error?.name) {
    case "NotAllowedError":
    case "SecurityError":
      return "Microphone permission was denied. Allow microphone access in your browser settings and try again.";
    case "NotFoundError":
    case "DevicesNotFoundError":
      return "No microphone device was found. Connect a microphone and try again.";
    case "NotReadableError":
    case "TrackStartError":
      return "The microphone is already in use by another app or browser tab.";
    case "OverconstrainedError":
      return "Your microphone does not support the requested recording settings.";
    case "AbortError":
      return "Microphone startup was interrupted. Please try again.";
    default:
      return error?.message || "Unable to start microphone recording.";
  }
}
