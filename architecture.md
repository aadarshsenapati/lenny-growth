# Architecture

## System overview

```
┌────────────┐      HTTPS/JSON      ┌───────────────┐
│  Frontend   │  ───────────────▶  │   FastAPI      │
│  (React)    │  ◀───────────────  │   Backend      │
└────────────┘                     └──────┬────────┘
                                            │
                     ┌──────────────────────┼───────────────────────┐
                     ▼                      ▼                       ▼
            ┌────────────────┐     ┌────────────────┐      ┌────────────────┐
            │  Skill Router   │     │  FAISS Vector   │      │  MySQL          │
            │  (rule-based)   │     │  Store (local)  │      │                 │
            └───────┬────────┘     └────────────────┘      └────────────────┘
                     │
        ┌────────────┼─────────────┐
        ▼            ▼             ▼
  grounded_qa     ship30       artifact
   skill          skill         skill
        │            │             │
        └────────────┴─────────────┘
                     ▼
            ┌────────────────┐
            │  LLM Provider   │──▶ Groq (cloud, free tier)
            │  Abstraction    │──▶ Ollama (local, mandatory for demo)
            └────────────────┘
```

## Database schema (MySQL)

**`chat_sessions`**
| column | type | notes |
|---|---|---|
| id | uuid, pk | |
| title | varchar(255) | |
| user_id | varchar(255) | simple string scoping, no auth in v1 |
| llm_provider | varchar(32) | default provider for this session |
| created_at / updated_at | timestamptz | |

**`messages`**
| column | type | notes |
|---|---|---|
| id | uuid, pk | |
| session_id | uuid, fk → chat_sessions, `ON DELETE CASCADE` | |
| role | varchar(16) | `user` \| `assistant` \| `system` |
| content | text | |
| skill_used | varchar(64), nullable | `grounded_qa` \| `ship30` \| `artifact` |
| citations | jsonb, nullable | `[{source, episode, chunk_id, score}]` |
| llm_provider | varchar(32), nullable | provider that generated this message |
| latency_ms | int, nullable | |
| created_at | timestamptz | |

**`artifacts`**
| column | type | notes |
|---|---|---|
| id | uuid, pk | |
| session_id | uuid, fk → chat_sessions, `ON DELETE CASCADE` | |
| message_id | uuid, fk → messages, `ON DELETE SET NULL`, nullable | |
| kind | varchar(16) | `markdown` \| `html` |
| title | varchar(255) | |
| content | text | |
| created_at | timestamptz | |

A portable `UUID` `TypeDecorator` stores UUIDs as `CHAR(36)` on every
dialect it's used with — MySQL has no native UUID column type either, so
the exact same representation backs both the production MySQL database and
the fast in-memory SQLite database used by the unit test suite, with no
dialect branching and no test-only schema drift.

**Migrations**: schema changes are managed by Alembic
(`backend/migrations/`), not by ad-hoc `create_all()` calls in application
code. `0001_initial.py` creates all three tables (InnoDB, `utf8mb4`) with
the indexes above. The Docker image's `entrypoint.sh` runs
`alembic upgrade head` before starting the API, so `docker compose up`
always converges to the latest schema; native/local runs do the same via
`alembic upgrade head` (see README → Quickstart).

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | DB, FAISS index, and LLM reachability status |
| POST | `/sessions` | Create a session |
| GET | `/sessions?user_id=` | List a user's sessions |
| GET | `/sessions/{id}` | Get one session |
| GET | `/sessions/{id}/messages` | Full message history for a session |
| DELETE | `/sessions/{id}` | Delete a session (cascades messages/artifacts) |
| POST | `/chat` | Send a message; routes to a skill; returns the reply |
| GET | `/artifacts/session/{id}` | List artifacts for a session |
| GET | `/artifacts/{id}` | Fetch one artifact |

All request/response bodies are typed Pydantic models (`app/db/schemas.py`).
Errors are raised as typed `AppError` subclasses (`app/core/exceptions.py`)
and converted to a consistent JSON shape `{error, detail, code}` by a global
exception handler, so the frontend can branch on `code` rather than parsing
message strings.

## Ingestion / retrieval flow

1. Transcript `.txt`/`.md` files in `data/transcripts/` are read by
   `ingest_transcripts.py`. Each **file = one episode**; the filename becomes
   the `episode` label used in citations, and the relative path becomes
   `source`.
2. `chunker.py` splits each transcript into ~400-token chunks with 60-token
   overlap (token-counted via `tiktoken`), so chunks are context-window-safe
   and retrieval doesn't lose material at boundaries.
3. `faiss_store.build_index()` embeds every chunk with
   `sentence-transformers/all-MiniLM-L6-v2` (small, CPU-only, free) and
   writes a `IndexFlatIP` FAISS index (cosine similarity via L2-normalized
   vectors) plus a parallel `metadata.json` to `FAISS_INDEX_DIR`.
4. At query time, `rag_service.retrieve()` embeds the user's question,
   searches the index, and returns the top-k chunks **plus a `grounded`
   boolean** — `true` only if at least one result clears
   `MIN_SIMILARITY_SCORE` (default 0.25). This is the mechanism behind the
   "acknowledge when the material doesn't support an answer" requirement.
5. Every retrieved chunk carries its `episode`, `source` file path, and
   `chunk_id` (e.g. `ep-142-casey-winters::chunk-3`) all the way through to
   the API response's `citations`, so an answer is always traceable back to
   an exact transcript excerpt.
6. **Refresh**: re-running `ingest_transcripts.py` fully rebuilds the index
   (documented trade-off vs. incremental updates in the script's docstring —
   appropriate at this corpus size). `reload_vector_store()` lets a running
   server pick up a rebuilt index without a restart.

## Agent routing

`app/agent/router.py` uses explicit regex trigger patterns rather than a
model-based classifier:
- Ship 30 triggers (`"ship 30"`, `"atomic essay"`, `"write an essay"`, ...) →
  **ship30 skill**
- Artifact triggers (`"artifact"`, `"markdown doc"`, `"html snippet"`,
  `"render this as"`, ...) → **artifact skill**
- everything else → **grounded_qa skill** (the safe default)

This is intentionally simple and auditable: an evaluator can read the
pattern list and predict routing behavior exactly, rather than debugging an
LLM-based router's occasional misclassification. The trade-off is reduced
flexibility for oddly-phrased requests — documented as a known limitation
and a natural place to swap in an LLM-based intent classifier later.

## Model configuration / toggle

`app/config.py` exposes `LLM_PROVIDER=groq|ollama`. `app/agent/llm_provider.py`
defines a single `LLMClient` protocol with `GroqClient` and `OllamaClient`
implementations; `get_llm_client(provider)` is the only place that branches
on provider. Every skill calls `llm.complete(...)` against that interface, so
**no skill or route code changes when switching providers** — only the env
var (server-wide default) or the `llm_provider` field on a chat request
(per-request override, driven by the frontend toggle).

**Fallback behavior:** if the selected provider is unreachable, the request
fails fast with a typed `LLMProviderUnavailableError` / `LLMTimeoutError`
(503/504) rather than hanging or silently switching providers — silent
fallback was rejected because it would hide which model actually produced an
answer, undermining trust in citations and grounding claims. The UI surfaces
a specific, actionable message per provider (see `design.md` "Error states").

### Agent framework choice
The assignment lists the Anthropic Claude Agent SDK or Pi Coding Agent as the
suggested agent layer. **This build uses a lightweight hand-rolled
skill-router + provider-abstraction instead, calling the Groq API directly**,
per explicit direction for this build (free-tier cost, low friction). The
skill/tool boundaries (`grounded_qa`, `ship30`, `artifact`) mirror what an
Agent SDK's tool-calling would express, so swapping in the Claude Agent SDK
later mainly means replacing `router.py`'s regex dispatch with SDK-native
tool-use routing — the skills themselves (`app/agent/skills/*.py`) would need
minimal changes since they're already structured as independent, single-
purpose functions with clear inputs/outputs.

## Artifact security

Generated artifacts are treated as **untrusted output** at every layer:

1. **Prompt-level constraints** (`artifact_skill.py`): the HTML system prompt
   forbids `<script>`, inline event handlers, and external resource loads,
   and requires a single self-contained fragment.
2. **Server-side sanitization** (`sanitize_html()`): regex-strips any
   `<script>` tags, `on*=` event handler attributes, `javascript:` URLs, and
   external `src`/`href` values that make it past the prompt, before the
   content is ever persisted or returned.
3. **Sandboxed rendering** (frontend `ArtifactViewer.jsx`): HTML artifacts
   render inside `<iframe sandbox="allow-same-origin">` — note **"allow-scripts"
   is deliberately omitted**, so even a payload that slipped through layers
   1–2 cannot execute. Markdown artifacts render via `react-markdown`, which
   does not interpret raw HTML by default, giving the same no-script
   guarantee through a different mechanism.

**What the viewer permits:** static HTML structure and inline CSS, rendered
visually.
**What it blocks:** any JavaScript execution, any network requests
initiated from within the artifact, and links to `javascript:` URLs.
**Why layered defense:** relying on the model to never emit unsafe markup is
not sufficient on its own (prompt injection, jailbreaks); relying on regex
sanitization alone is fragile against clever encodings; the sandboxed iframe
is the actual security boundary, with the earlier layers reducing noise/scope
rather than being the sole guarantee.

## Deployment topology

- **backend**: FastAPI container (`backend/Dockerfile`), talks to MySQL
  over the network (host machine, a containerized `db` service, or a hosted
  MySQL instance — see `docker-compose.yml`) and to Ollama over the Docker
  network.
- **frontend**: static Vite build served via `serve` (`frontend/Dockerfile`).
- **ollama**: official `ollama/ollama` image, model pulled once via
  `docker compose exec ollama ollama pull llama3.1:8b`.
- **MySQL**: not containerized by default — the app is configured to reach
  a MySQL server you already run (e.g. via MySQL Workbench), matching the
  assignment's "store in PostgreSQL... you may use Supabase or Railway"
  persistence requirement in spirit while substituting MySQL as the
  relational engine (documented deviation, see `PRD.md` "Assumptions").
  `docker-compose.yml` includes a commented-out `db` (MySQL) service for a
  fully containerized alternative.
- **FAISS index**: lives on a bind-mounted `./data` volume so it survives
  container restarts and is rebuildable via the ingestion CLI without
  rebuilding the image.

## Observability & resilience

- Structured logs (`structlog`) at every skill boundary: `skill_routed`,
  `retrieval_below_threshold`, `groq_call_failed`, `faiss_index_missing`,
  `app_error` (with typed `code`), `unhandled_error`.
- `/health` reports **independently** whether DB, FAISS index, and the
  configured LLM provider are reachable — the app can start and serve
  `/health` even if the FAISS index hasn't been built yet or the DB is
  briefly unreachable, rather than crashing at boot.
- Every external call (Groq, Ollama, MySQL) is wrapped so failures surface
  as typed `AppError`s with a stable `code`, not raw stack traces to the
  client — see the errors table in `README.md` → Troubleshooting.
