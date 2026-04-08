import { useEffect, useState } from "react";
import Chat from "./components/Chat.jsx";
import Teach from "./components/Teach.jsx";
import { getStats } from "./api.js";

export default function App() {
  const [tab, setTab] = useState("chat");
  const [stats, setStats] = useState({ totalChunks: 0 });

  async function refreshStats() {
    try {
      const s = await getStats();
      setStats(s);
    } catch {
      // backend not running yet — ignore
    }
  }

  useEffect(() => {
    refreshStats();
  }, []);

  return (
    <div className="app">
      <header className="header">
        <h1>RAG Chatbot</h1>
        <div className="meta">
          <span className="badge">{stats.totalChunks} chunks</span>
          <nav className="tabs">
            <button
              className={tab === "chat" ? "tab active" : "tab"}
              onClick={() => setTab("chat")}
            >
              Chat
            </button>
            <button
              className={tab === "teach" ? "tab active" : "tab"}
              onClick={() => setTab("teach")}
            >
              Teach
            </button>
          </nav>
        </div>
      </header>

      <main className="main">
        {tab === "chat" ? (
          <Chat onAfterAction={refreshStats} />
        ) : (
          <Teach onAfterAction={refreshStats} />
        )}
      </main>

      <footer className="footer">
        Powered by Gemini · grounded answers only
      </footer>
    </div>
  );
}
