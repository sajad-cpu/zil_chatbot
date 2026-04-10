import { useEffect, useRef, useState } from "react";
import { sendChat } from "../api.js";
import ChatSidebar from "./ChatSidebar.jsx";

export default function Chat({ onAfterAction }) {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef(null);

  // Load conversations from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem("zil_conversations");
    if (saved) {
      const convs = JSON.parse(saved);
      setConversations(convs);
      if (convs.length > 0 && !currentConversationId) {
        const latest = convs[0];
        setCurrentConversationId(latest.id);
        setMessages(latest.messages);
      }
    }
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  // Save conversations to localStorage whenever they change
  useEffect(() => {
    if (conversations.length > 0 || currentConversationId) {
      localStorage.setItem("zil_conversations", JSON.stringify(conversations));
    }
  }, [conversations]);

  function createNewConversation() {
    const id = `conv_${Date.now()}`;
    const now = new Date();
    const title = `Chat ${now.toLocaleDateString()}`;

    const newConv = {
      id,
      title,
      messages: [],
      createdAt: now.toISOString(),
    };

    setConversations([newConv, ...conversations]);
    setCurrentConversationId(id);
    setMessages([]);
    setError("");
    setInput("");
  }

  function selectConversation(id) {
    const conv = conversations.find((c) => c.id === id);
    if (conv) {
      setCurrentConversationId(id);
      setMessages(conv.messages);
      setError("");
    }
  }

  function deleteConversation(id) {
    const updated = conversations.filter((c) => c.id !== id);
    setConversations(updated);

    if (currentConversationId === id) {
      if (updated.length > 0) {
        selectConversation(updated[0].id);
      } else {
        createNewConversation();
      }
    }
  }

  function clearAllHistory() {
    if (confirm("Are you sure? This will delete all conversations.")) {
      setConversations([]);
      setCurrentConversationId(null);
      setMessages([]);
      setError("");
      localStorage.removeItem("zil_conversations");
    }
  }

  function updateCurrentConversation(newMessages) {
    const updated = conversations.map((c) => {
      if (c.id === currentConversationId) {
        return { ...c, messages: newMessages };
      }
      return c;
    });
    setConversations(updated);
  }

  async function handleSend(e) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setError("");
    const userMsg = { role: "user", content: text };
    const next = [...messages, userMsg];
    setMessages(next);
    updateCurrentConversation(next);
    setInput("");
    setLoading(true);

    try {
      const res = await sendChat(text, messages);
      const updated = [
        ...next,
        { role: "assistant", content: res.answer, sources: res.sources },
      ];
      setMessages(updated);
      updateCurrentConversation(updated);
    } catch (err) {
      setError(err.message);
      const errMsg = [
        ...next,
        { role: "assistant", content: `⚠️ ${err.message}`, error: true },
      ];
      setMessages(errMsg);
      updateCurrentConversation(errMsg);
    } finally {
      setLoading(false);
    }
  }

  // Initialize with first conversation if none exists
  useEffect(() => {
    if (conversations.length === 0 && !currentConversationId) {
      createNewConversation();
    }
  }, [conversations.length, currentConversationId]);

  const currentTitle =
    conversations.find((c) => c.id === currentConversationId)?.title ||
    "New Chat";

  return (
    <div className="chat-container">
      <ChatSidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onNewChat={createNewConversation}
        onSelectConversation={selectConversation}
        onDeleteConversation={deleteConversation}
        onClearAllHistory={clearAllHistory}
      />

      <section className="chat">
        <div className="chat-header">
          <h2>{currentTitle}</h2>
        </div>

        <div className="messages" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="empty">
              <div className="empty-icon">💬</div>
              <p>Start a conversation</p>
              <p className="empty-hint">
                Ask me anything about Zil Money. I'll answer based on our knowledge base.
              </p>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              <div className={`bubble ${m.error ? "error" : ""}`}>{m.content}</div>
              {m.sources && m.sources.length > 0 && (
                <details className="sources">
                  <summary>📎 {m.sources.length} source{m.sources.length > 1 ? "s" : ""}</summary>
                  <ul>
                    {m.sources.map((s, idx) => (
                      <li key={idx}>
                        <span className="score">{s.score.toFixed(2)}</span>
                        <span className="source-text">{s.text.substring(0, 100)}...</span>
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

        {error && <div className="error-bar">{error}</div>}

        <form className="composer" onSubmit={handleSend}>
          <input
            type="text"
            value={input}
            placeholder="Ask a question about Zil Money…"
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            autoFocus
          />
          <button type="submit" disabled={loading || !input.trim()}>
            {loading ? "..." : "Send"}
          </button>
        </form>
      </section>
    </div>
  );
}
