import { AnimatePresence, motion } from "framer-motion";

export default function ToastStack({ toasts, onDismiss }) {
  return (
    <div className="fixed right-4 top-4 z-50 w-[calc(100vw-2rem)] max-w-sm space-y-2">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: -12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12, scale: 0.98 }}
            className={`rounded-lg border p-3 shadow-card backdrop-blur-xl ${
              toast.type === "error"
                ? "border-rose-300/30 bg-rose-500/15 text-rose-50"
                : "border-cyan-200/25 bg-cyan-400/15 text-cyan-50"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm">{toast.message}</p>
              <button className="text-xs text-current/70 hover:text-current" onClick={() => onDismiss(toast.id)}>
                Dismiss
              </button>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
