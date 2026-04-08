import { useEffect, useRef, useState } from "react";
import { sendChat } from "../api.js";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef(null);

  // Auto-scroll on new messages.
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  async function handleSend(e) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setError("");
    const userMsg = { role: "user", content: text };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput("");
    setLoading(true);

    try {
      // Send only the prior turns as history (the current message goes in `message`).
      const res = await sendChat(text, messages);
      setMessages([
        ...next,
        { role: "assistant", content: res.answer, sources: res.sources },
      ]);
    } catch (err) {
      setError(err.message);
      setMessages([
        ...next,
        { role: "assistant", content: `⚠️ ${err.message}`, error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    setMessages([]);
    setError("");
  }

  return (
    <section className="chat">
      <div className="chat-toolbar">
        <button
          className="ghost"
          onClick={handleClear}
          disabled={messages.length === 0}
        >
          Clear chat
        </button>
      </div>

      <div className="messages" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="empty">
            Ask me something. I'll answer only from the knowledge you've taught me.
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="bubble">{m.content}</div>
            {m.sources && m.sources.length > 0 && (
              <details className="sources">
                <summary>{m.sources.length} sources</summary>
                <ul>
                  {m.sources.map((s, idx) => (
                    <li key={idx}>
                      <span className="score">{s.score.toFixed(2)}</span>{" "}
                      <span>{s.text}</span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        ))}

        {loading && (
          <div className="msg assistant">
            <div className="bubble loading">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        )}
      </div>

      {error && <div className="error">{error}</div>}

      <form className="composer" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          placeholder="Ask a question…"
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </section>
  );
}
