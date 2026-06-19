const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed.");
  }
  return res.json();
}

export async function fetchDocuments() {
  const res = await fetch(`${API_BASE}/api/documents`);
  if (!res.ok) throw new Error("Could not load your document list.");
  return res.json();
}

export async function askQuestion(question, docId) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, doc_id: docId || null }),
  });
  if (!res.ok) throw new Error("The chat request failed.");
  return res.json();
}
