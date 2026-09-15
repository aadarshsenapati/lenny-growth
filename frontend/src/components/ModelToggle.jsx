export default function ModelToggle({ provider, onChange, health }) {
  const ollamaUp = health?.ollama_available;
  const dbUp = health?.database;

  return (
    <div className="model-toggle">
      <div className="provider-buttons">
        <button
          className={provider === "groq" ? "active" : ""}
          onClick={() => onChange("groq")}
          title="Cloud LLM (Groq, free tier)"
        >
          ☁️ Groq (cloud)
        </button>
        <button
          className={provider === "ollama" ? "active" : ""}
          onClick={() => onChange("ollama")}
          title="Local LLM via Ollama — mandatory for the demo"
        >
          💻 Ollama (local)
        </button>
      </div>
      <div className="status-pills">
        <span className={`pill ${dbUp ? "ok" : "warn"}`}>DB {dbUp ? "connected" : "unreachable"}</span>
        <span className={`pill ${ollamaUp ? "ok" : "warn"}`}>
          Ollama {ollamaUp ? "running" : "not detected"}
        </span>
      </div>
    </div>
  );
}
