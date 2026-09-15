import { useEffect, useState } from "react";
import { api } from "./api";
import SessionSidebar from "./components/SessionSidebar";
import ChatWindow from "./components/ChatWindow";
import ArtifactViewer from "./components/ArtifactViewer";
import ModelToggle from "./components/ModelToggle";

const USER_ID = "demo-user";

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [provider, setProvider] = useState("groq");
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [artifact, setArtifact] = useState(null);

  // Poll health so DB/Ollama status stays current without a manual refresh.
  useEffect(() => {
    const poll = async () => {
      try {
        setHealth(await api.health());
      } catch {
        setHealth({ status: "down", database: false, ollama_available: false });
      }
    };
    poll();
    const id = setInterval(poll, 15000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    refreshSessions();
  }, []);

  async function refreshSessions() {
    try {
      const list = await api.listSessions(USER_ID);
      setSessions(list);
      if (!activeSessionId && list.length > 0) {
        selectSession(list[0].id);
      }
    } catch (e) {
      setError("Could not load chat history: " + e.message);
    }
  }

  async function handleNewChat() {
    try {
      const session = await api.createSession(USER_ID, provider);
      setSessions((prev) => [session, ...prev]);
      setActiveSessionId(session.id);
      setMessages([]);
      setArtifact(null);
      setError(null);
    } catch (e) {
      setError("Could not start a new chat: " + e.message);
    }
  }

  async function selectSession(id) {
    setActiveSessionId(id);
    setArtifact(null);
    setError(null);
    try {
      const msgs = await api.getSessionMessages(id);
      setMessages(
        msgs.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          citations: m.citations,
        }))
      );
    } catch (e) {
      setError("Could not load messages: " + e.message);
    }
  }

  async function handleDeleteSession(id) {
    try {
      await api.deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setMessages([]);
      }
    } catch (e) {
      setError("Could not delete chat: " + e.message);
    }
  }

  async function handleSend(text) {
    let sessionId = activeSessionId;
    if (!sessionId) {
      const session = await api.createSession(USER_ID, provider);
      setSessions((prev) => [session, ...prev]);
      sessionId = session.id;
      setActiveSessionId(sessionId);
    }

    setMessages((prev) => [...prev, { id: `local-${Date.now()}`, role: "user", content: text }]);
    setLoading(true);
    setError(null);

    try {
      const resp = await api.sendChat(sessionId, text, provider);
      setMessages((prev) => [
        ...prev,
        {
          id: resp.message_id,
          role: "assistant",
          content: resp.content,
          citations: resp.citations,
          grounded: resp.grounded,
        },
      ]);
      if (resp.artifact) setArtifact(resp.artifact);
    } catch (e) {
      const friendly =
        e.code === "llm_provider_unavailable"
          ? provider === "ollama"
            ? "Ollama isn't reachable. Make sure `ollama serve` is running and the model is pulled."
            : "The cloud provider is unavailable. Check GROQ_API_KEY, or switch to Ollama."
          : e.code === "retrieval_index_missing"
          ? "No transcript index found yet. Run the ingestion script first."
          : e.message;
      setError(friendly);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={selectSession}
        onNewChat={handleNewChat}
        onDelete={handleDeleteSession}
      />
      <main className="main-panel">
        <header className="top-bar">
          <h1>Lenny Growth Assistant</h1>
          <ModelToggle provider={provider} onChange={setProvider} health={health} />
        </header>
        <div className="content-split">
          <ChatWindow messages={messages} onSend={handleSend} loading={loading} error={error} />
          <ArtifactViewer artifact={artifact} onClose={() => setArtifact(null)} />
        </div>
      </main>
    </div>
  );
}
