const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let body;
    try {
      body = await res.json();
    } catch {
      body = { detail: res.statusText };
    }
    const err = new Error(body.detail || "Request failed");
    err.code = body.code;
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  health: () => request("/health"),

  createSession: (userId = "anonymous", llmProvider) =>
    request("/sessions", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, llm_provider: llmProvider }),
    }),

  listSessions: (userId = "anonymous") => request(`/sessions?user_id=${encodeURIComponent(userId)}`),

  getSessionMessages: (sessionId) => request(`/sessions/${sessionId}/messages`),

  deleteSession: (sessionId) => request(`/sessions/${sessionId}`, { method: "DELETE" }),

  sendChat: (sessionId, message, llmProvider) =>
    request("/chat", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, message, llm_provider: llmProvider }),
    }),

  listArtifacts: (sessionId) => request(`/artifacts/session/${sessionId}`),
};
