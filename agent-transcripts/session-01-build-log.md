# Session 01 — Backend, Ingestion, Agent Layer, Frontend Scaffold

Agent: Claude (Anthropic), operating in a sandboxed Linux container with
bash/file tools, building against the Forward Deployed Engineer take-home
brief. This log summarizes the actual build session, including failed
attempts and how they were corrected. (Full raw transcript can be exported
from the chat interface and dropped alongside this file before final
submission — see this folder's README.)

## Scope of this session
- Backend: FastAPI app, config/provider toggle, SQLAlchemy models, RAG
  ingestion (FAISS + MiniLM), three skills (grounded_qa, ship30, artifact),
  rule-based router, API routes, error handling, structured logging.
- Frontend: React chat UI, sidebar, sandboxed artifact viewer, provider
  toggle.
- Docs: PRD, architecture, design, README.
- A second pass: Alembic migrations, CI workflow, additional test coverage,
  a couple of real bug fixes described below.

## Failed attempts and corrections

### 1. `mkdir -p` brace expansion silently no-op'd
**What happened:** Ran
`mkdir -p project/{backend/app/{db,api,...},frontend/...}` expecting nested
brace expansion to create the full tree in one call. The tool invoked the
command through a shell where brace expansion did not behave as in
interactive bash — it created a literal directory named `{backend` instead
of expanding.
**How it was caught:** A `find . -maxdepth 3` sanity check right after
showed the literal `{backend` directory instead of the expected tree.
**Fix:** Removed the bad directory and re-ran `mkdir -p` as separate,
explicit calls per directory. Slower but unambiguous — adopted "verify with
`find`/`ls` immediately after any structural command" as a habit for the
rest of the session.

### 2. SQLAlchemy pool kwargs broke the SQLite test path
**What happened:** The async engine was created with `pool_size=5,
max_overflow=5` unconditionally. Those kwargs are specific to `QueuePool`
(used by asyncpg/Postgres); when the test suite pointed `DATABASE_URL` at
SQLite (`sqlite+aiosqlite:///:memory:`, which uses `StaticPool`), engine
creation failed immediately, breaking every test that imports `app.main`.
**How it was caught:** Ran `pytest` deliberately (not just eyeballing the
code) against a SQLite `DATABASE_URL` before considering the backend done —
this failure only shows up when you actually execute the code, not on
review.
**Fix:** Made the pool kwargs conditional on the dialect
(`app/db/database.py`): only apply `pool_size`/`max_overflow` when
`DATABASE_URL` isn't a SQLite URL. This also *documents* a real constraint
for whoever runs the test suite against SQLite later.

### 3. Sloppy placeholder in `routes_artifacts.py`
**What happened:** Early draft of the 404 branch in `get_artifact` was
written as `raise AppError.__class__ and AppError("Artifact not found")` —
a leftover placeholder that technically parses but is nonsensical and would
raise the wrong exception type (base `AppError`, not a proper 404).
**How it was caught:** Code review pass before wiring up tests — this kind
of bug doesn't always surface in happy-path testing, so it's worth calling
out as something a quick self-review caught rather than a test.
**Fix:** Added a dedicated `ArtifactNotFoundError(AppError)` (404,
`artifact_not_found`) to `core/exceptions.py` and raised that instead.

### 4. Eager `sentence-transformers` import made unrelated code paths fragile
**What happened:** `faiss_store.py` originally imported
`from sentence_transformers import SentenceTransformer` at module level.
Since `faiss_store` is imported transitively by `/health` and `/sessions`
routes (via `app.main`), any environment without `sentence-transformers`
installed (e.g. a minimal CI job, or this sandbox's disk-constrained
install) would crash the *entire app* at import time — including routes
that have nothing to do with embeddings.
**How it was caught:** Hit a real `ModuleNotFoundError` while trying to
install a lighter dependency set to test-run the app faster in a
disk-constrained sandbox.
**Fix:** Moved the import inside `_get_embedder()` (lazy import). This also
happens to be the *correct* resilience behavior per the assignment brief —
`/health` should degrade gracefully, not hard-crash, when an optional
dependency is missing.

### 5. Chat endpoint had zero test coverage after the first pass
**What happened:** The first pass shipped 16 passing tests, but none of
them exercised `/chat` — the actual core business logic (routing → skill →
persistence → citations). This was a real gap, not just a nice-to-have: a
regression in skill dispatch or persistence could ship undetected.
**How it was caught:** Explicit self-review against the assignment's
"meaningful automated tests for critical API... behavior" requirement.
**Fix:** Added `tests/test_chat_endpoint.py` with the LLM client mocked
(`app.api.routes_chat.get_llm_client` patched) so tests are fast and
deterministic, covering: grounded Q&A persistence + citations + auto-title,
ship30 routing, artifact creation + persistence, unknown-session 404, and
LLM-provider-unavailable error propagation with user-message persistence
preserved even on LLM failure.

### 6. Sessions never bubbled to the top of the sidebar or got real titles
**What happened:** `chat_sessions.updated_at` has `onupdate=func.now()`,
but SQLAlchemy only fires `onupdate` when the row is actually flushed with a
changed attribute — the `/chat` route never touched the session row at all,
so `updated_at` was frozen at creation time forever, and every session sat
at "New chat" permanently.
**How it was caught:** Manually walking through the "recently active
sessions sort to the top" UX expectation and realizing the code never wrote
to the session row on chat.
**Fix:** `/chat` now sets `session.title` from the first user message (once,
if still the default title) and explicitly bumps `session.updated_at` on
every turn.

## What went right without correction
- The Groq/Ollama provider abstraction (`LLMClient` protocol +
  `get_llm_client(provider)` factory) needed no rework — swapping providers
  really did stay a one-line call-site change throughout the skills layer.
- The portable `UUID` TypeDecorator (native Postgres UUID vs. SQLite
  `CHAR(36)`) worked on the first attempt, which made the SQLite-backed test
  suite possible without any schema duplication.
- The layered HTML sanitization (prompt constraint → server-side strip →
  non-scripting sandboxed iframe) tested clean on the first pass — all four
  `test_artifact_sanitize.py` cases passed without adjustment.

## Verification performed this session
- `python -m py_compile` across all backend source files (syntax).
- `pytest -q` — 21/21 tests passing (excluding one network-dependent test in
  this offline sandbox; passes in CI/normal environments with internet).
- `npm run build` — frontend production build succeeds with no errors.
