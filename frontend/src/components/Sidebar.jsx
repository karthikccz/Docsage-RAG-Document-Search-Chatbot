import FileUpload from "./FileUpload.jsx";

export default function Sidebar({ documents, uploading, onUpload, activeDocId, onSelectDoc, error }) {
  return (
    <aside className="flex h-full w-72 flex-col border-r border-white/10 bg-panel">
      <div className="px-5 pt-6 pb-4">
        <h1 className="font-display text-2xl text-paper">
          Docsage<span className="text-amber">.</span>
        </h1>
        <p className="mt-1 text-xs text-muted">Chat with your PDFs, with page-level receipts.</p>
      </div>

      <div className="px-5">
        <FileUpload onUpload={onUpload} uploading={uploading} />
        {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
      </div>

      <div className="mt-6 flex-1 overflow-y-auto px-5">
        <p className="mb-2 text-xs uppercase tracking-wide text-muted">Scope</p>

        <button
          onClick={() => onSelectDoc(null)}
          className={`mb-1 w-full rounded-md px-3 py-2 text-left text-sm transition-colors
            ${activeDocId === null ? "bg-amber-soft text-amber" : "text-paper/80 hover:bg-white/5"}`}
        >
          All documents
        </button>

        {documents.map((doc) => (
          <button
            key={doc.doc_id}
            onClick={() => onSelectDoc(doc.doc_id)}
            title={doc.filename}
            className={`mb-1 w-full truncate rounded-md px-3 py-2 text-left text-sm transition-colors
              ${activeDocId === doc.doc_id ? "bg-amber-soft text-amber" : "text-paper/80 hover:bg-white/5"}`}
          >
            {doc.filename}
            <span className="ml-2 text-xs text-muted">{doc.chunks} chunks</span>
          </button>
        ))}

        {documents.length === 0 && (
          <p className="mt-2 text-xs text-muted">No documents indexed yet.</p>
        )}
      </div>
    </aside>
  );
}
