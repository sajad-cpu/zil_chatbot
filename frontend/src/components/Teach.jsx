import { useState } from "react";
import { trainBot, clearKnowledge } from "../api.js";

export default function Teach({ onAfterAction }) {
  const [content, setContent] = useState("");
  const [status, setStatus] = useState(null); // {type: 'success'|'error', text: string}
  const [loading, setLoading] = useState(false);

  async function handleTrain(e) {
    e.preventDefault();
    if (!content.trim() || loading) return;
    setLoading(true);
    setStatus(null);
    try {
      const res = await trainBot(content);
      setStatus({
        type: "success",
        text: `Trained! Added ${res.chunksAdded} chunks (${res.totalChunks} total).`,
      });
      setContent("");
      onAfterAction?.();
    } catch (err) {
      setStatus({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  }

  async function handleClear() {
    if (!confirm("Wipe all stored knowledge? This cannot be undone.")) return;
    setLoading(true);
    setStatus(null);
    try {
      await clearKnowledge();
      setStatus({ type: "success", text: "Knowledge base cleared." });
      onAfterAction?.();
    } catch (err) {
      setStatus({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="teach">
      <h2>Teach the bot</h2>
      <p className="hint">
        Paste any text — documentation, notes, FAQs. It will be chunked,
        embedded, and stored. The bot will only answer from this knowledge.
      </p>

      <form onSubmit={handleTrain}>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={12}
          placeholder="Paste knowledge here…"
          disabled={loading}
        />
        <div className="row">
          <button type="submit" disabled={loading || !content.trim()}>
            {loading ? "Training…" : "Train"}
          </button>
          <button
            type="button"
            className="danger"
            onClick={handleClear}
            disabled={loading}
          >
            Clear knowledge
          </button>
        </div>
      </form>

      {status && (
        <div className={`notice ${status.type}`}>{status.text}</div>
      )}
    </section>
  );
}
