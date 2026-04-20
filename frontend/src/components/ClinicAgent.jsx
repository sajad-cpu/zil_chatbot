import { useEffect, useRef, useState } from "react";
import { createClinicSession, sendClinicMessage } from "../api.js";

export default function ClinicAgent() {
  const [sessionId, setSessionId] = useState(null);
  const [state, setState] = useState({ messages: [], available_options: [] });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    async function bootstrap() {
      try {
        setLoading(true);
        const res = await createClinicSession();
        setSessionId(res.session_id);
        setState(res.state);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    bootstrap();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [state.messages, loading]);

  async function handleSend(message) {
    const text = message.trim();
    if (!text || loading) return;

    try {
      setLoading(true);
      setError("");
      const res = await sendClinicMessage(text, sessionId);
      setSessionId(res.session_id);
      setState(res.state);
      setInput("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleReset() {
    try {
      setLoading(true);
      setError("");
      const res = await createClinicSession();
      setSessionId(res.session_id);
      setState(res.state);
      setInput("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const activeOptions = state.available_options || [];

  return (
    <div className="clinic-page">
      <div className="clinic-shell native">
        <div className="clinic-header">
          <div>
            <p className="clinic-eyebrow">CarePlus</p>
            <h1>Clinic AI Assistant</h1>
            <p className="clinic-subtitle">
              A built-in appointment booking flow running from the same backend as your
              RAG chatbot.
            </p>
          </div>
          <div className="clinic-actions">
            <button className="clinic-secondary-btn" onClick={handleReset} disabled={loading}>
              New Booking
            </button>
            <a className="clinic-back-link" href="/">
              Open RAG Chatbot
            </a>
          </div>
        </div>

        <div className="clinic-chat" ref={scrollRef}>
          {state.messages.length === 0 && !loading && (
            <div className="clinic-empty-state">
              <h2>No messages yet</h2>
              <p>Start a clinic booking conversation to continue.</p>
            </div>
          )}

          {state.messages.map((message, index) => (
            <div key={index} className={`clinic-msg ${message.role}`}>
              <div className="clinic-bubble">
                <div className="clinic-message-text">{message.content}</div>
                {message.options && message.options.length > 0 && index === state.messages.length - 1 && (
                  <div className="clinic-option-grid">
                    {message.options.map((option) => (
                      <button
                        key={option}
                        className="clinic-option-btn"
                        onClick={() => handleSend(option)}
                        disabled={loading}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="clinic-msg assistant">
              <div className="clinic-bubble loading">Thinking...</div>
            </div>
          )}
        </div>

        {activeOptions.length > 0 && state.messages.length > 0 && (
          <div className="clinic-sticky-options">
            {activeOptions.map((option) => (
              <button
                key={option}
                className="clinic-option-btn"
                onClick={() => handleSend(option)}
                disabled={loading}
              >
                {option}
              </button>
            ))}
          </div>
        )}

        {error && <div className="error-bar">{error}</div>}

        <form
          className="clinic-composer"
          onSubmit={(event) => {
            event.preventDefault();
            handleSend(input);
          }}
        >
          <input
            type="text"
            value={input}
            placeholder="Type your message or choose an option..."
            onChange={(event) => setInput(event.target.value)}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
