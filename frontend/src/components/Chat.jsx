import { useEffect, useRef, useState } from "react";
import {
  sendChat,
  listConversations,
  createConversation,
  getConversation,
  deleteConversation,
} from "../api.js";
import ChatSidebar from "./ChatSidebar.jsx";

export default function Chat({ onAfterAction, onLogout }) {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loadingConversations, setLoadingConversations] = useState(true);
  const scrollRef = useRef(null);

  // Load conversations from API on mount
  useEffect(() => {
    async function loadConversations() {
      try {
        setLoadingConversations(true);
        const convs = await listConversations();
        setConversations(convs);
        if (convs.length > 0 && !currentConversationId) {
          const latest = convs[0];
          setCurrentConversationId(latest.id);
          await selectConversation(latest.id);
        }
      } catch (err) {
        console.error("Failed to load conversations:", err);
      } finally {
        setLoadingConversations(false);
      }
    }

    loadConversations();
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  async function createNewConversation() {
    try {
      const now = new Date();
      const title = `Chat ${now.toLocaleDateString()}`;
      const newConv = await createConversation(title);

      setConversations([newConv, ...conversations]);
      setCurrentConversationId(newConv.id);
      setMessages([]);
      setError("");
      setInput("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function selectConversation(id) {
    try {
      const conv = await getConversation(id);
      setCurrentConversationId(id);
      setMessages(
        conv.messages.map((m) => ({
          role: m.role,
          content: m.content,
        }))
      );
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteConversation(id) {
    try {
      await deleteConversation(id);
      const updated = conversations.filter((c) => c.id !== id);
      setConversations(updated);

      if (currentConversationId === id) {
        if (updated.length > 0) {
          await selectConversation(updated[0].id);
        } else {
          await createNewConversation();
        }
      }
    } catch (err) {
      setError(err.message);
    }
  }

  async function clearAllHistory() {
    if (confirm("Are you sure? This will delete all conversations.")) {
      try {
        // Delete all conversations
        for (const conv of conversations) {
          await deleteConversation(conv.id);
        }
        setConversations([]);
        setCurrentConversationId(null);
        setMessages([]);
        setError("");
      } catch (err) {
        setError(err.message);
      }
    }
  }

  async function handleSend(e) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || loading || !currentConversationId) return;

    setError("");
    const userMsg = { role: "user", content: text };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput("");
    setLoading(true);

    try {
      const res = await sendChat(text, currentConversationId, messages);
      const updated = [
        ...next,
        { role: "assistant", content: res.answer, sources: res.sources },
      ];
      setMessages(updated);
    } catch (err) {
      setError(err.message);
      const errMsg = [
        ...next,
        { role: "assistant", content: `⚠️ ${err.message}`, error: true },
      ];
      setMessages(errMsg);
    } finally {
      setLoading(false);
    }
  }

  // Initialize with first conversation if none exists
  useEffect(() => {
    if (!loadingConversations && conversations.length === 0 && !currentConversationId) {
      createNewConversation();
    }
  }, [loadingConversations, conversations.length, currentConversationId]);

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
        onDeleteConversation={handleDeleteConversation}
        onClearAllHistory={clearAllHistory}
        onLogout={onLogout}
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
