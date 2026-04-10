import { useEffect, useState } from "react";
import Chat from "./components/Chat.jsx";
import Teach from "./components/Teach.jsx";
import { getStats } from "./api.js";

export default function App() {
  const [activeTab, setActiveTab] = useState("chat");
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
      {activeTab === "chat" ? (
        <>
          <Chat onAfterAction={refreshStats} />
          <div className="floating-menu">
            <button
              className="menu-btn teach-btn"
              onClick={() => setActiveTab("teach")}
              title="Teach the bot (add knowledge)"
            >
              📚 Teach
            </button>
            <div className="stats-badge">{stats.totalChunks} chunks</div>
          </div>
        </>
      ) : (
        <>
          <div className="teach-wrapper">
            <button
              className="back-btn"
              onClick={() => setActiveTab("chat")}
            >
              ← Back to Chat
            </button>
            <Teach onAfterAction={refreshStats} />
          </div>
        </>
      )}
    </div>
  );
}
