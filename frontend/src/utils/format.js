export function formatBytes(bytes = 0) {
  if (!bytes) return "Unknown";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export function formatDuration(seconds = 0) {
  const safeSeconds = Number(seconds) || 0;
  const minutes = Math.floor(safeSeconds / 60);
  const remainder = Math.round(safeSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${remainder}`;
}

export function formatTimer(ms = 0) {
  return formatDuration(Math.floor(ms / 1000));
}
