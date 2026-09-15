# PRD — The Lenny Growth Assistant

## 1. Forward Deployment Brief

### User and problem
**Primary user:** a product manager or growth lead on the client's team who
wants fast, trustworthy answers to "what do experienced operators say about
X" without listening to 400+ hours of podcast content, and who occasionally
needs to turn that knowledge into shareable written content (an internal memo,
a Ship 30-style essay, a one-pager) without hand-formatting it themselves.

**Job to be done:** "When I'm making a product or growth decision, help me
quickly find what credible operators have actually said about this exact
problem, and let me turn that into something I can share or publish, without
me needing to know anything about prompts, RAG, or which model is running."

**Pain removed:** hours of manual podcast/newsletter searching, uncertainty
about whether an LLM's answer is actually grounded in real source material,
and the extra step of manually reformatting an answer into a polished
document.

### Success metric
Primary: **% of chat responses that are grounded** (i.e., backed by retrieved
transcript chunks above the similarity threshold, `grounded: true` in the API
response) — target **≥ 90%** of in-scope product/growth questions on a
representative eval set of ~30 questions.

Secondary (operational): **p50 response latency < 4s** for grounded Q&A on
the cloud provider, and **zero unhandled 500s** across a scripted smoke test
covering missing API key, Ollama down, empty retrieval, and DB unavailable.

### Assumptions
Because the brief left several details to the implementer, this build
assumes:
1. "Users" are internal team members (PMs/growth), not end-customers — so no
   auth/SSO is required for v1; a simple `user_id` string scopes sessions.
2. A small-to-medium transcript corpus (dozens to low hundreds of episodes)
   is realistic for a v1 demo — this justifies a **flat FAISS index** (exact
   search) instead of an ANN index, and a **full-rebuild ingestion** model
   instead of incremental upserts.
3. "Local model that works comfortably on your machine" means an 8B-class
   Ollama model (e.g. `llama3.1:8b`), not a 70B model, to keep the demo
   runnable on a laptop.
4. Groq was substituted as the cloud provider in place of the Anthropic Claude
   Agent SDK / Pi Coding Agent, per direct instruction for this build (free
   tier, fast inference). This is a **documented deviation** from the
   assignment's suggested agent frameworks — see `architecture.md` "Agent
   framework choice" for the trade-off.
5. Real Lenny's Podcast transcripts are not bundled in this repo (no bulk
   transcript API exists and redistributing full transcripts raises its own
   licensing questions) — two short, clearly-labeled **fictional sample
   transcripts** are included so the pipeline is demoable end-to-end; real
   transcripts should be dropped into `data/transcripts/` before a real
   evaluation.
6. "Session" means one conversation thread; multi-user collaboration within a
   single session is out of scope.
7. **MySQL was substituted for Postgres** as the relational persistence
   layer, per direct instruction for this build (a MySQL instance managed
   via MySQL Workbench was already available). This is a **documented
   deviation** from the assignment's "store in PostgreSQL... you may use
   Supabase or Railway" wording — the schema, ORM models, and Alembic
   migrations target MySQL specifically (InnoDB, `utf8mb4`, `CHAR(36)`
   UUIDs since MySQL has no native UUID type). Nothing in the retrieval,
   agent, or API layers is Postgres- or MySQL-specific, so this swap only
   touched the persistence layer (`app/db/`, `migrations/`) — see
   `architecture.md` "Database schema" for details.

### Scope choices

**Included (v1):**
- Grounded conversational Q&A over transcripts (RAG via FAISS), with
  follow-up context and an explicit "not enough material" path.
- Ship 30 for 30-style essay generation as a distinct skill with encoded
  structural rules.
- Markdown/HTML artifact generation with an in-app, sandboxed Artifact Viewer.
- Session persistence (MySQL): sessions, messages, artifacts.
- Cloud (Groq) + local (Ollama) model toggle, visible in the UI.
- Structured logging, typed error handling, `/health` endpoint.
- Docker Compose one-command startup, `.env.example`, automated tests.

**Explicitly excluded (v1), and why:**
- **Authentication/SSO** — internal tool assumption (#1 above); would be
  straightforward to layer in with the existing `user_id` field.
- **Multi-tenant orgs / roles** — no requirement in the brief; adds
  significant surface area for a take-home scope.
- **Streaming token-by-token responses** — the assignment prioritizes
  correctness/groundedness/architecture over UX polish; a single
  request/response per turn is simpler to test and reason about. Noted as
  the top "next iteration" item.
- **Automatic transcript refresh/scraping** — no public bulk API exists for
  Lenny's transcripts; ingestion is a deliberate, explicit CLI step instead
  of a background scraper, both for licensing caution and reliability.
- **Fine-grained per-skill model routing** (e.g. cheap model for routing,
  strong model for essays) — the router is a lightweight rule-based classifier
  today; swapping to a second cheap LLM call for routing is a natural
  extension, not required for correctness at this scale.

### Risks and trade-offs
| Risk | Mitigation in this build |
|---|---|
| **Hallucination** | System prompts constrain answers to retrieved context only; retrieval score threshold flags low-confidence answers as `grounded: false` and the UI surfaces a warning. |
| **Latency** | Flat FAISS search is O(n) but fast at this corpus size; local Ollama is inherently slower — documented as a known trade-off, not hidden. |
| **Cost** | Groq free tier + a small local embedding model (MiniLM) keep ingestion and inference free for the demo. |
| **Local-model quality** | 8B local models are noticeably weaker than cloud models at following the strict grounding instructions — the same system prompt is used for both, and this quality gap is called out explicitly in the demo video per the deliverable requirement. |
| **Data leakage** | Sessions are scoped by `user_id`; no cross-session context bleed (each request loads only that session's message history). |
| **Unsafe artifact rendering** | Multi-layer defense: prompt constraints → server-side HTML sanitization (strip `<script>`, event handlers, `javascript:` URLs, external resource loads) → sandboxed `<iframe>` render with scripts disabled. See `architecture.md`. |

## 2. Flows
1. **New chat → grounded question → follow-up question** (session context
   preserved) → **citations shown**.
2. **Ask a question → "turn that into a Ship 30 for 30 essay"** → essay
   generated as chat content, following the 1,250-word structural skill.
3. **Ask a question → "generate a markdown/HTML artifact"** → artifact
   persisted and rendered in the Artifact Viewer alongside chat.
4. **Switch provider (Groq ↔ Ollama) mid-conversation** → next message uses
   the newly selected provider; UI reflects which provider produced each
   response.
5. **Failure flows**: Ollama unreachable, Groq key missing, empty retrieval
   results, DB unreachable — each returns a typed error the UI turns into a
   specific, actionable message (see `architecture.md` "Resilience").

## 3. Acceptance criteria
- [ ] A new session can be created and messages persist across a page reload.
- [ ] Two sessions never share conversation context.
- [ ] A grounded answer includes at least one citation with a traceable
      `episode`/`source`/`chunk_id`.
- [ ] A question clearly outside the transcript corpus returns
      `grounded: false` and an explicit "not enough material" style answer,
      not a confident hallucination.
- [ ] "Ship 30" trigger phrases produce an essay ~1,250 words with heading
      structure and a closing takeaway.
- [ ] Artifact requests produce a persisted artifact visible in the Artifact
      Viewer, and HTML artifacts cannot execute a test `<script>alert(1)</script>`
      payload injected via a crafted prompt.
- [ ] Switching LLM_PROVIDER (env) or the in-app toggle changes which
      provider serves the next response, with no code changes.
- [ ] `/health` accurately reports DB, FAISS index, and LLM reachability.
- [ ] `docker compose up --build` brings up a working stack from a clean
      clone, given a filled-in `.env`.

## 4. Implementation plan (as built)
1. Config layer + provider abstraction (Groq/Ollama behind one interface).
2. Data models + persistence (sessions/messages/artifacts).
3. Ingestion pipeline (chunk → embed → FAISS) + sample transcripts.
4. RAG service + grounded_qa skill.
5. Ship30 skill + artifact skill (with sanitization).
6. Rule-based skill router.
7. FastAPI routes, error handling, health check.
8. Automated tests (routing, chunking, sanitization, session persistence, RAG
   grounding threshold).
9. React frontend: chat, sidebar, sandboxed artifact viewer, provider toggle.
10. Docker Compose, docs, agent transcripts, demo video.
