export default function SessionSidebar({ sessions, activeSessionId, onSelect, onNewChat, onDelete }) {
  return (
    <aside className="sidebar">
      <button className="new-chat-btn" onClick={onNewChat}>
        + New chat
      </button>
      <div className="session-list">
        {sessions.length === 0 && <p className="empty-hint">No chats yet</p>}
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`session-item ${s.id === activeSessionId ? "active" : ""}`}
            onClick={() => onSelect(s.id)}
          >
            <span className="session-title">{s.title || "New chat"}</span>
            <button
              className="delete-btn"
              title="Delete chat"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(s.id);
              }}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
