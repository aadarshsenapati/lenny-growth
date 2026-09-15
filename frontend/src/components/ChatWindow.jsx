import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function Citations({ citations }) {
  if (!citations || citations.length === 0) return null;
  return (
    <div className="citations">
      <span className="citations-label">Sources:</span>
      {citations.map((c, i) => (
        <span key={i} className="citation-chip" title={`score: ${c.score.toFixed(2)}`}>
          {c.episode || c.source}
        </span>
      ))}
    </div>
  );
}

export default function ChatWindow({ messages, onSend, loading, error, groundedWarning }) {
  const [draft, setDraft] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const submit = (e) => {
    e.preventDefault();
    if (!draft.trim() || loading) return;
    onSend(draft.trim());
    setDraft("");
  };

  return (
    <div className="chat-window">
      <div className="message-list">
        {messages.length === 0 && (
          <div className="empty-state">
            <h2>Ask about product & growth from Lenny's Podcast</h2>
            <ul>
              <li>"What do guests say about pricing PLG products?"</li>
              <li>"Turn that into a Ship 30 for 30 essay"</li>
              <li>"Generate a markdown artifact summarizing this thread"</li>
            </ul>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`message ${m.role}`}>
            <div className="message-role">{m.role === "user" ? "You" : "Assistant"}</div>
            <div className="message-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
            </div>
            {m.role === "assistant" && <Citations citations={m.citations} />}
            {m.role === "assistant" && m.grounded === false && (
              <div className="grounding-warning">
                ⚠ The transcripts didn't clearly support this answer — treat it with caution.
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="message-role">Assistant</div>
            <div className="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}
        {error && <div className="error-banner">{error}</div>}
        <div ref={bottomRef} />
      </div>
      <form className="composer" onSubmit={submit}>
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask a question, or request an essay / artifact..."
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) submit(e);
          }}
        />
        <button type="submit" disabled={loading || !draft.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
