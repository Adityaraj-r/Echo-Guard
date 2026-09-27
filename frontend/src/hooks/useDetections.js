import { useCallback, useEffect, useState } from "react";
import { deleteDetection, fetchDetections } from "../services/api.js";

export function useDetections(onError) {
  const [history, setHistory] = useState([]);
  const [deletionEnabled, setDeletionEnabled] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState("");

  const loadHistory = useCallback(async () => {
    setIsLoadingHistory(true);
    setHistoryError("");
    try {
      const response = await fetchDetections({ limit: 20 });
      setHistory(response.items);
      setDeletionEnabled(response.deletion_enabled !== false);
    } catch (exception) {
      const message = exception.message || "Could not load detection history.";
      setHistoryError(message);
      onError?.(message);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [onError]);

  const removeDetection = useCallback(
    async (id) => {
      try {
        await deleteDetection(id);
        setHistory((items) => items.filter((item) => item.id !== id));
      } catch (exception) {
        const message = exception.message || "Could not delete detection.";
        setHistoryError(message);
        onError?.(message);
      }
    },
    [onError],
  );

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  return {
    history,
    deletionEnabled,
    historyError,
    isLoadingHistory,
    loadHistory,
    removeDetection,
  };
}
