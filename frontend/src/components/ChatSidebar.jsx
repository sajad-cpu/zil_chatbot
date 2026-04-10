import { useEffect, useState } from "react";

export default function ChatSidebar({
  conversations,
  currentConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  onClearAllHistory,
}) {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <aside className={`sidebar ${isOpen ? "open" : "closed"}`}>
      <div className="sidebar-header">
        <button
          className="sidebar-toggle"
          onClick={() => setIsOpen(!isOpen)}
          title={isOpen ? "Close sidebar" : "Open sidebar"}
        >
          ☰
        </button>
        {isOpen && <h2>Zil Chat</h2>}
      </div>

      {isOpen && (
        <>
          <button className="new-chat" onClick={onNewChat}>
            <span className="icon">+</span>
            New Chat
          </button>

          <div className="conversations-list">
            {conversations.length === 0 ? (
              <div className="empty-state">No conversations yet</div>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`conversation-item ${
                    conv.id === currentConversationId ? "active" : ""
                  }`}
                >
                  <button
                    className="conv-name"
                    onClick={() => onSelectConversation(conv.id)}
                    title={conv.title}
                  >
                    {conv.title}
                  </button>
                  <button
                    className="conv-delete"
                    onClick={() => onDeleteConversation(conv.id)}
                    title="Delete conversation"
                  >
                    ✕
                  </button>
                </div>
              ))
            )}
          </div>

          <div className="sidebar-footer">
            <button
              className="clear-all"
              onClick={onClearAllHistory}
              disabled={conversations.length === 0}
            >
              Clear all history
            </button>
          </div>
        </>
      )}
    </aside>
  );
}
