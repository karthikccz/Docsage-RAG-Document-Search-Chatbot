import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import { uploadDocument, fetchDocuments, askQuestion } from "./api/client.js";

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [activeDocId, setActiveDocId] = useState(null); // null = search all docs
  const [messages, setMessages] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");

  const loadDocuments = async () => {
    try {
      setDocuments(await fetchDocuments());
    } catch {
      // Quietly skip -- the empty-state UI already covers this case.
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleUpload = async (file) => {
    setUploading(true);
    setError("");
    try {
      const res = await uploadDocument(file);
      await loadDocuments();
      setActiveDocId(res.doc_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Indexed "${res.filename}" into ${res.chunks_indexed} chunks. Ask away.`,
        },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleSend = async (question) => {
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setAsking(true);
    try {
      const res = await askQuestion(question, activeDocId);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, sources: res.sources },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Something went wrong: ${err.message}` },
      ]);
    } finally {
      setAsking(false);
    }
  };

  const scopeLabel =
    activeDocId === null
      ? "All indexed documents"
      : documents.find((d) => d.doc_id === activeDocId)?.filename || "Selected document";

  return (
    <div className="flex h-screen bg-ink">
      <Sidebar
        documents={documents}
        uploading={uploading}
        onUpload={handleUpload}
        activeDocId={activeDocId}
        onSelectDoc={setActiveDocId}
        error={error}
      />
      <ChatWindow messages={messages} onSend={handleSend} asking={asking} scopeLabel={scopeLabel} />
    </div>
  );
}
