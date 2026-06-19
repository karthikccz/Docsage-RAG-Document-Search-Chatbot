export default function MessageBubble({ role, content, sources }) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-2xl rounded-lg px-4 py-3 text-sm leading-relaxed
          ${isUser ? "bg-amber text-ink" : "bg-panel text-paper/90 border border-white/10"}`}
      >
        <p className="whitespace-pre-wrap">{content}</p>

        {sources?.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5 border-t border-white/10 pt-2">
            {sources.map((s, i) => (
              <span
                key={i}
                title={s.content}
                className="cursor-help rounded-full bg-white/5 px-2 py-0.5 text-xs text-muted"
              >
                {s.filename} · p.{s.page}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
