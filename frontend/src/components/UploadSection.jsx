import { motion } from "framer-motion";
import { FileAudio, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";

const acceptedFormats = ".wav,.aac,.m4a,.flac,.mp3,.aiff,.ogg,.wma,.dsf,.dff";

export default function UploadSection({ file, onFile }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  function handleFiles(files) {
    const selected = files?.[0];
    if (selected) onFile(selected);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className={`drop-zone ${dragging ? "drop-zone-active" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        handleFiles(event.dataTransfer.files);
      }}
    >
      <div className="grid h-14 w-14 place-items-center rounded-lg bg-cyan-300/10 text-cyan-200">
        <FileAudio size={28} />
      </div>
      <div className="text-center">
        <p className="text-lg font-semibold text-slate-50">{file ? file.name : "Drop forensic audio sample"}</p>
        <p className="mt-1 text-sm text-slate-400">WAV, MP3, FLAC, AAC, OGG, AIFF, WMA, DSF, DFF</p>
      </div>
      <input ref={inputRef} hidden type="file" accept={acceptedFormats} onChange={(event) => handleFiles(event.target.files)} />
      <button className="primary-button" onClick={() => inputRef.current?.click()}>
        <UploadCloud size={18} />
        Choose file
      </button>
    </motion.div>
  );
}
