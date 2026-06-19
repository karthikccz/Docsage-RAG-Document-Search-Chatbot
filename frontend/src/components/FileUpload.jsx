import { useRef, useState } from "react";

export default function FileUpload({ onUpload, uploading }) {
  const inputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFiles = (files) => {
    const file = files?.[0];
    if (file) onUpload(file);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragActive(true);
      }}
      onDragLeave={() => setDragActive(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragActive(false);
        handleFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      className={`relative cursor-pointer rounded-md border border-dashed px-4 py-6 text-center transition-colors
        ${dragActive ? "border-amber bg-amber-soft/40" : "border-white/15 hover:border-white/30"}`}
    >
      {/* folded-corner glyph: a nod to the PDFs this tool reads */}
      <svg
        viewBox="0 0 24 24"
        className="mx-auto mb-2 h-6 w-6 text-amber"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
      >
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <path d="M14 2v6h6" />
      </svg>

      <p className="text-sm text-paper/80">
        {uploading ? "Indexing your PDF…" : "Drop a PDF, or click to browse"}
      </p>
      <p className="mt-1 text-xs text-muted">Only .pdf is supported right now</p>

      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}
