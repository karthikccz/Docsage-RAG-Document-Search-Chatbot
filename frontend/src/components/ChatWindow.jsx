import { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble.jsx";

export default function ChatWindow({ messages, onSend, asking, scopeLabel }) {
  const [input, setInput] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || asking) return;
    onSend(trimmed);
    setInput("");
  };

  return (
    <div className="flex h-full flex-1 flex-col">
      <div className="border-b border-white/10 px-6 py-4">
        <p className="text-xs uppercase tracking-wide text-muted">Asking</p>
        <p className="text-sm text-paper/90">{scopeLabel}</p>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
        {messages.length === 0 && (
          <div className="mt-16 text-center text-muted">
            <p className="font-display text-lg text-paper/70">Nothing indexed into a question yet.</p>
            <p className="mt-1 text-sm">Upload a PDF on the left, then ask it anything.</p>
          </div>
        )}

        {messages.map((m, i) => (
          <MessageBubble key={i} role={m.role} content={m.content} sources={m.sources} />
        ))}

        {asking && (
          <div className="flex justify-start">
            <div className="rounded-lg border border-white/10 bg-panel px-4 py-3 text-sm text-muted">
              Reading the relevant pages…
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-white/10 px-6 py-4">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask something about your document…"
          className="flex-1 rounded-md border border-white/10 bg-ink px-3 py-2 text-sm text-paper outline-none focus:border-amber"
        />
        <button
          type="submit"
          disabled={asking}
          className="rounded-md bg-amber px-4 py-2 text-sm font-medium text-ink disabled:opacity-50"
        >
          Ask
        </button>
      </form>
    </div>
  );
}
