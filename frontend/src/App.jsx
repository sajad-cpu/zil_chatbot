import { useEffect, useState } from "react";
import Chat from "./components/Chat.jsx";
import Teach from "./components/Teach.jsx";
import AuthPage from "./components/AuthPage.jsx";
import ClinicAgent from "./components/ClinicAgent.jsx";
import { getStats, getCurrentUser } from "./api.js";

export default function App() {
  const [pathname, setPathname] = useState(window.location.pathname);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [activeTab, setActiveTab] = useState("chat");
  const [stats, setStats] = useState({ totalChunks: 0 });

  useEffect(() => {
    function handlePopState() {
      setPathname(window.location.pathname);
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  // Validate stored token on mount
  useEffect(() => {
    if (pathname === "/clinic-ai") {
      setIsCheckingAuth(false);
      return;
    }

    async function validateToken() {
      const token = localStorage.getItem("auth_token");
      if (!token) {
        setIsLoggedIn(false);
        setIsCheckingAuth(false);
        return;
      }

      try {
        await getCurrentUser();
        setIsLoggedIn(true);
      } catch {
        // Token is invalid, clear it
        localStorage.removeItem("auth_token");
        setIsLoggedIn(false);
      } finally {
        setIsCheckingAuth(false);
      }
    }

    validateToken();
  }, [pathname]);

  if (pathname === "/clinic-ai") {
    return <ClinicAgent />;
  }

  async function refreshStats() {
    try {
      const s = await getStats();
      setStats(s);
    } catch {
      // backend not running yet — ignore
    }
  }

  async function handleAuthSuccess() {
    setIsLoggedIn(true);
    setActiveTab("chat");
    refreshStats();
  }

  function handleLogout() {
    localStorage.removeItem("auth_token");
    setIsLoggedIn(false);
    setActiveTab("chat");
  }

  if (isCheckingAuth) {
    return <div className="app loading-auth">Loading...</div>;
  }

  if (!isLoggedIn) {
    return <AuthPage onAuthSuccess={handleAuthSuccess} />;
  }

  return (
    <div className="app">
      {activeTab === "chat" ? (
        <>
          <Chat onAfterAction={refreshStats} onLogout={handleLogout} />
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
