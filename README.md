# The Lenny Growth Assistant

A grounded conversational assistant over Lenny's Podcast transcripts, with a Ship 30 for 30 essay skill, Markdown/HTML artifact generation, and a sandboxed in-app Artifact Viewer.

See also: [`PRD.md`](./PRD.md) (discovery brief, scope, acceptance criteria), [`architecture.md`](./architecture.md) (schema, API, retrieval flow, security), [`design.md`](./design.md) (UI/UX principles), [`DEMO_SCRIPT.md`](./DEMO_SCRIPT.md) (talking points/checklist for the demo video), [`agent-transcripts/`](./agent-transcripts) (build session log, including failed attempts and how they were fixed).

## Architecture at a glance

* **Backend**: FastAPI, async SQLAlchemy → MySQL, FAISS vector store, Groq (cloud) / Ollama (local) behind one LLM interface.
* **Frontend**: React (Vite), sandboxed iframe Artifact Viewer.
* **Skills**: `grounded_qa` (default), `ship30` (essay generation), `artifact` (Markdown/HTML generation), dispatched by a rule-based router.

## Prerequisites

* Docker + Docker Compose (recommended path), **or** Python 3.11+ and Node 20+ for running services natively.
* A running MySQL server (e.g. managed via MySQL Workbench) reachable from wherever the backend runs, for `DATABASE_URL`.
* A free [Groq API key](https://console.groq.com/keys) for the cloud provider — see **"Choosing a Groq model"** below before you set this up, since Groq's available model catalog is account/region-specific and changes over time.
* [Ollama](https://ollama.com) installed locally — **mandatory for the demo** per the assignment brief.

## Quickstart (Docker Compose)

```bash
git clone <this-repo>
cd lenny-growth-assistant
cp .env.example .env
# edit .env: set DATABASE_URL (MySQL) and GROQ_API_KEY (see below)

docker compose up --build

# pull the local model once the ollama container is up:
docker compose exec ollama ollama pull llama3.1:8b
```

Then, in a separate terminal, run ingestion once so the assistant has something to retrieve from (sample transcripts are included so this works out of the box). Database migrations run automatically on container start via `entrypoint.sh` (`alembic upgrade head`), so no manual migration step is needed with Docker Compose:

```bash
docker compose exec backend python -m app.ingestion.ingest_transcripts
```

Services:

* Frontend: http://localhost:5173
* Backend API: http://localhost:8000 (docs at `/docs`)
* Health check: http://localhost:8000/health

## Running natively (without Docker)

The fastest path is the setup script, which creates `.env`, sets up the backend venv, runs migrations, ingests the sample transcripts, and installs frontend dependencies in one go:

```bash
./scripts/setup.sh
```

Or step by step:

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # edit as needed; loaded from repo root
alembic upgrade head
python -m app.ingestion.ingest_transcripts
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Ollama

Run separately:

```bash
ollama serve
ollama pull llama3.1:8b
```

> **Windows / PowerShell note:** `.env` is resolved relative to the directory `uvicorn` is *run from*, not the repo root. If you run `uvicorn app.main:app --reload` from inside `backend/`, make sure a `.env` file exists at `backend/.env` (copy the root one there if needed).
>
> Also, `--reload` watches Python file changes but does **not** re-read `.env` for an already-configured `Settings` object (it's cached via `@lru_cache`) — after editing `.env`, fully stop (`Ctrl+C`) and restart `uvicorn`; don't rely on the auto-reloader to pick up env changes.

## Choosing a Groq model

`GROQ_MODEL` in `.env` must be a model your specific Groq API key actually has access to — Groq's free-tier catalog varies by account and changes as models are added/deprecated, so a model name that works in a tutorial or in an older version of this README may 404 for you (`model_not_found`) even with a perfectly valid API key.

**Before setting `GROQ_MODEL`, list what your key can use:**

```bash
python -c "
from groq import Groq
client = Groq(api_key='YOUR_GROQ_API_KEY')
for m in client.models.list().data:
    print(m.id)
"
```

This project was built and tested against Groq's `openai/gpt-oss-*` model family, which was available on a standard free-tier key at build time:

| Model                 | Notes                                                                                                                        |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `openai/gpt-oss-20b`  | Faster, lighter — good default for iterating and for the demo's grounded Q&A skill.                                          |
| `openai/gpt-oss-120b` | Larger, higher-quality output — better for the Ship 30 essay skill where structure/coherence over ~1,250 words matters more. |

Your key's catalog may also include (or later include) `llama-3.x` variants, `qwen/*`, or others — if `list()` shows a `llama-3.1-8b-instant` or `llama-3.3-70b-versatile` entry for your account, either works fine too; this app makes no assumptions about which specific model family is active beyond "an OpenAI-chat-completions-compatible model Groq serves."

If you ever see this in the logs:

```text
groq_call_failed  error=Error code: 404 - {'error': {'message': 'The model `X` does not exist or you do not have access to it.'...}}
```

that's not an API key problem — it's `GROQ_MODEL` naming a model your key can't reach right now. Re-run the `models.list()` snippet above and update `.env` accordingly, then fully restart the backend.

## Switching LLM providers

Set `LLM_PROVIDER=groq` or `LLM_PROVIDER=ollama` in `.env` (server-wide default), or use the toggle in the top bar of the UI to override it per session/request — no code changes required either way. `/health` reports whether the currently configured provider (and Ollama specifically) is reachable.

## Environment variables

See [`.env.example`](./.env.example) for the full list with defaults. Key required variables:

| Variable          | Required                              | Purpose                                                                    |
| ----------------- | ------------------------------------- | -------------------------------------------------------------------------- |
| `DATABASE_URL`    | Yes                                   | MySQL connection string (async, `mysql+aiomysql://...`)                    |
| `GROQ_API_KEY`    | Only if using `LLM_PROVIDER=groq`     | Cloud inference                                                            |
| `GROQ_MODEL`      | Only if using `LLM_PROVIDER=groq`     | Must be a model your key has access to — see "Choosing a Groq model" above |
| `LLM_PROVIDER`    | No (default `groq`)                   | `groq` | `ollama`                                                          |
| `OLLAMA_BASE_URL` | No (default `http://localhost:11434`) | Local inference endpoint                                                   |
| `OLLAMA_MODEL`    | No (default `llama3.1:8b`)            | Must already be pulled via `ollama pull`                                   |
| `FAISS_INDEX_DIR` | No                                    | Where the vector index is written/read                                     |

Never commit a filled-in `.env` — only `.env.example` is checked in.

If your MySQL password contains special characters, percent-encode it first:

```bash
python3 -c "import urllib.parse; print(urllib.parse.quote('YOUR-PASSWORD', safe=''))"
```

## Tests

**Backend** (21 automated tests: health, skill routing, transcript chunking, artifact HTML sanitization, session persistence via isolated in-memory SQLite, RAG grounding-threshold logic, and full `/chat` endpoint flows with a mocked LLM — routing, persistence, citations, auto-titling, and error propagation):

```bash
cd backend
pytest -q
```

> Note: `test_chunker.py` downloads a tokenizer vocabulary file on first run (`tiktoken`); it needs outbound internet access once, then caches locally.

### Manual UI test plan

Run after `docker compose up`:

1. Create a new chat → ask a question covered by the sample transcripts → confirm the answer cites `sample-plg-pricing-episode` or `sample-onboarding-activation-episode`.
2. Ask a follow-up question ("what about for enterprise?") → confirm the assistant uses prior context, not just the latest message.
3. Ask something clearly outside the corpus (e.g. "what's the weather today?") → confirm the response acknowledges insufficient material rather than inventing an answer, and shows the low-confidence warning.
4. Say "turn that into a Ship 30 for 30 essay" → confirm ~1,250 words, headings, bullets, bold emphasis, and a specific takeaway.
5. Say "generate an HTML artifact summarizing this" → confirm the Artifact Viewer opens beside the chat and renders correctly.
6. Refresh the page → confirm the session and its messages reload from persistence.
7. Toggle Groq ↔ Ollama → send a message on each → confirm the response shows the expected provider and the status pills update.
8. Stop the Ollama container/process → send a message on Ollama → confirm a specific, actionable error banner (not a generic failure).
9. Delete a session → confirm it disappears from the sidebar and its messages/artifacts are gone.

## Production readiness

**Filling in `.env` makes this runnable — it does not make it production-ready.** Those are different bars, and this project deliberately targets the first one (a working, demoable, well-architected v1) rather than overclaiming the second. Below is an honest accounting of what's already in place versus what a real production rollout would still need.

### Already production-grade

* Async FastAPI + SQLAlchemy throughout, no blocking calls in request paths.
* Schema managed by Alembic migrations (not ad-hoc `create_all()`), with a matching MySQL/SQLite-portable `UUID` type.
* Typed error handling (`AppError` subclasses → consistent JSON shape) and structured logging at every skill/provider/DB boundary.
* Config-driven LLM provider switching (no code changes to go cloud ↔ local).
* Layered artifact-rendering security (prompt constraints → server-side sanitization → non-scripting sandboxed iframe) — see `architecture.md`.
* CI (`.github/workflows/ci.yml`) running tests + a frontend build on every push, so regressions are caught pre-merge.
* Graceful degradation: `/health` reports DB/FAISS/LLM reachability independently rather than crashing; missing optional dependencies (e.g. the embedding model) don't take down unrelated routes.
* **Error surfacing that reflects the real cause.** Provider misconfiguration (missing key, unreachable Ollama, invalid model name) surfaces as a typed 503/504 with the actual upstream message, not swallowed by a generic 500 — see "Known issues fixed during build" below.

### Known issues fixed during build

Two infrastructure bugs surfaced during local development and are fixed in this codebase (also logged in `agent-transcripts/`):

1. **`tenacity.RetryError` masking the real error as a 500.**

   Groq calls are wrapped in a retry decorator; when the underlying cause was a permanent config error (missing API key), tenacity retried it anyway and then re-raised a `RetryError` instead of the original `LLMProviderUnavailableError` — which fell through FastAPI's typed `AppError` handler into a generic, unhelpful 500.

   Fixed by excluding `LLMProviderUnavailableError` from the retry policy (`retry_if_not_exception_type`) and adding a `RetryError` exception handler in `main.py` as a safety net that unwraps and re-dispatches to the typed handler.

2. **`aiomysql` + SQLAlchemy 2.0.35 `ping()` signature mismatch.**

   SQLAlchemy's `pool_pre_ping` calls `dbapi_connection.ping()` with no arguments, but this version of aiomysql's async connection wrapper requires `reconnect` to be passed explicitly, raising a `TypeError` on nearly every DB checkout.

   Fixed with a small monkeypatch in `app/db/database.py` that defaults `reconnect=True` when the argument is omitted, which also makes it safe to re-enable `pool_pre_ping=True` for MySQL (it was previously disabled as a workaround, losing the dead-connection detection it provides).

### Gaps to close before real production use

| Gap                                                 | Why it matters                                                                                                                             | What closing it looks like                                                                                                                                                                                               |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **No authentication**                               | `user_id` is a free-text string anyone can spoof — no login, no enforced session ownership.                                                | Add real auth (an auth provider like Clerk/Auth0, or your own IdP) and scope every query by the authenticated user, not a client-supplied string.                                                                        |
| **No rate limiting**                                | Nothing stops abusive or buggy clients from hammering Groq or the DB.                                                                      | Add per-user/IP rate limiting at the API gateway or in FastAPI middleware (e.g. `slowapi`).                                                                                                                              |
| **CORS defaults to localhost**                      | `CORS_ORIGINS` in `.env.example` is a dev default.                                                                                         | Set it to your real frontend origin(s) only — never a wildcard — in production `.env`.                                                                                                                                   |
| **No TLS termination**                              | Docker Compose serves plain HTTP.                                                                                                          | Put a reverse proxy (nginx/Caddy) in front, or rely on your host's TLS (Railway, Fly.io, Vercel, etc. handle this automatically).                                                                                        |
| **`SESSION_SECRET` is unused**                      | It exists in config but nothing signs cookies/tokens with it yet — dead config today.                                                      | Wire it into real session/auth token signing once auth is added, or remove it if auth is handled entirely by a third party.                                                                                              |
| **`.env` as the only secrets story**                | Fine for a demo; risky as the sole mechanism long-term.                                                                                    | Move secrets to your platform's secret manager (your host's env/secrets settings, AWS Secrets Manager, etc.) instead of a file on disk.                                                                                  |
| **No monitoring/alerting**                          | Structured logs exist but go nowhere — an outage is only visible if someone is watching the terminal.                                      | Ship logs to an aggregator (e.g. Better Stack, Datadog) and add uptime/error-rate alerting (e.g. Sentry for exceptions).                                                                                                 |
| **No load testing**                                 | The FAISS index is a single in-process flat index with no concurrency tuning; untested under real traffic.                                 | Load-test with a tool like `locust` or `k6`, and re-evaluate the ANN-vs-flat-index trade-off if the corpus or QPS grows.                                                                                                 |
| **No backup/retention policy**                      | No automated backups configured for the MySQL instance, and there's no data-deletion story.                                                | Configure scheduled `mysqldump`/binlog-based backups (or use a managed MySQL host with automated backups); add a deletion/export flow if this ever touches real user data (GDPR-style requests).                         |
| **Groq model/catalog drift**                        | Groq's available free-tier models change over time and by account, so a hardcoded `GROQ_MODEL` can silently 404 after a catalog change.    | Add a startup check that calls `models.list()` and validates `GROQ_MODEL` is actually available, failing `/health` clearly instead of only failing at first chat request.                                                |
| **Groq free tier**                                  | Rate-limited, not intended for production load.                                                                                            | Move to a paid tier, or add a second cloud provider as a fallback behind the same `LLMClient` interface.                                                                                                                 |
| **Single backend instance / single MySQL instance** | No horizontal scaling or DB replication configured, though the app is already close to stateless (all state lives in MySQL/FAISS-on-disk). | Run multiple backend replicas behind a load balancer; add MySQL read replicas or move to a managed MySQL host (e.g. PlanetScale, RDS) for HA; move the FAISS index to shared/networked storage so replicas stay in sync. |

None of these are surprises — they're the standard gap between "a well-architected v1" and "a production system," and the architecture here (stateless-by-design backend, config-driven providers, typed errors) was built specifically to make closing them additive rather than requiring a rewrite.

## Future work

Beyond the production-readiness gaps above, a few product/UX directions would be natural next iterations:

* **Streaming responses.** Currently a deliberate scope cut (see `PRD.md` "Scope choices") — the typing indicator is a placeholder for real token-by-token streaming, which would meaningfully improve perceived latency, especially on the local Ollama path.
* **LLM-based skill routing.** The current rule-based router (`app/agent/router.py`) is simple and fully auditable but will misroute oddly-phrased requests that don't match its regex patterns. A lightweight second LLM call (or a small classifier) as an optional routing mode would handle more natural phrasing without losing the deterministic fallback.
* **Incremental transcript ingestion.** Ingestion currently does a full rebuild of the FAISS index on every run — fine at the current corpus size, but re-embedding hundreds of hours of transcripts on every small addition won't scale. An upsert-by-chunk-id path would let new episodes be added without touching unrelated existing chunks.
* **Per-skill model routing.** Right now every skill uses the same configured provider/model. A cheaper/faster model for `grounded_qa` and a stronger model for `ship30` (which needs more coherence over long output) is a natural extension once cost/latency tradeoffs matter more.
* **Multi-turn artifact refinement.** Artifacts are generated fresh each time; there's no "make the takeaway punchier" follow-up flow yet that edits an existing artifact in place rather than regenerating it wholesale.
* **Second cloud provider as fallback.** If Groq's free tier is rate-limited or a specific model becomes unavailable, having a second provider (e.g. OpenAI, Anthropic, or another Groq-compatible endpoint) behind the same `LLMClient` interface would let the app degrade to an alternate cloud option instead of only falling back to local Ollama.
* **Startup model validation.** As noted in the production gaps table, validating `GROQ_MODEL` against the live `models.list()` response at startup (and surfacing it clearly in `/health`) would turn a first-request 503 into an immediate, obvious startup warning.

## UI improvements

The current UI (`design.md`) intentionally prioritized a working three-pane layout, clear error states, and citation traceability over visual polish.

Natural next steps for the interface:

* **Real streaming UI**, replacing the three-dot typing indicator with token-by-token rendering once backend streaming lands (see Future Work).
* **Editable/regenerable artifacts** — an "iterate on this" affordance in the Artifact Viewer instead of only Copy/Close, tied to the multi-turn artifact refinement work above.
* **Citation hover previews** — currently a citation chip shows the similarity score on hover (per `design.md`); showing a short snippet of the actual matched transcript text on hover (not just the score) would make trust-checking a citation faster without leaving the chat.
* **Session search/filtering** in the sidebar — today sessions are a flat, recency-sorted list with no search, which will get unwieldy with dozens of past conversations.
* **Persistent provider-per-session indicator in the message list**, not just the top bar — so scrolling back through a long conversation makes it obvious which provider generated which specific answer, especially useful after switching providers mid-session.
* **Mobile artifact viewer polish** — the current mobile behavior (full-screen view reached via a button) works but hasn't been tested against very long Markdown artifacts; a proper scroll/collapse treatment for long content would help.
* **Dark/light theme toggle** — the current dark-only theme was a documented aesthetic choice (`design.md`), not a hard requirement; adding a light theme option would broaden usability preference-wise.
* **Inline retry button on error banners** — today a failed message (e.g. provider unavailable) requires re-typing/resending; a one-click "Retry" action on the error banner itself would reduce friction, especially for transient Ollama timeouts.

## Troubleshooting

| Symptom                                                                                                                                    | Likely cause                                                                                                | Fix                                                                                                                                                                                                                                               |
| ------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/health` shows `faiss_index_loaded: false`                                                                                                | Ingestion hasn't run yet                                                                                    | `python -m app.ingestion.ingest_transcripts`                                                                                                                                                                                                      |
| Chat returns `retrieval_index_missing`                                                                                                     | Same as above                                                                                               | Same as above                                                                                                                                                                                                                                     |
| `alembic upgrade head` fails with "table already exists"                                                                                   | Tables were created manually outside Alembic                                                                | Drop the tables in MySQL Workbench, or `alembic stamp head` if the schema already matches                                                                                                                                                         |
| Chat returns `llm_provider_unavailable` (Groq), detail mentions `GROQ_API_KEY is not configured`                                           | `.env` isn't being found from the directory you launched `uvicorn` from, or the key is missing/empty        | Confirm `backend/.env` exists (not just the repo-root one) and contains a real key; verify with `python -c "from app.config import get_settings; print(repr(get_settings().groq_api_key))"`; then **fully restart** uvicorn (not just `--reload`) |
| Chat returns `llm_provider_unavailable` (Groq), detail mentions `model_not_found` / `does not exist or you do not have access to it`       | `GROQ_MODEL` names a model your API key can't currently access                                              | Run the `models.list()` snippet in "Choosing a Groq model" above and set `GROQ_MODEL` to one it actually lists, then fully restart the backend                                                                                                    |
| `/chat` returns a generic 500 with `RetryError` in the detail instead of a clear 503                                                       | Older code where a retried call's terminal exception wasn't unwrapped                                       | Ensure `GroqClient.complete` uses `retry_if_not_exception_type(LLMProviderUnavailableError)` and `main.py` has the `RetryError` exception handler (see "Known issues fixed during build" above)                                                   |
| `/sessions` or any DB-touching route 500s with `AsyncAdapt_aiomysql_connection.ping() missing 1 required positional argument: 'reconnect'` | Known SQLAlchemy 2.0.35 + aiomysql 0.2.0 incompatibility with `pool_pre_ping`                               | Apply the `_patch_aiomysql_ping()` monkeypatch in `app/db/database.py` (see "Known issues fixed during build" above)                                                                                                                              |
| Chat returns `llm_provider_unavailable` (Ollama)                                                                                           | `ollama serve` not running, or model not pulled                                                             | `ollama serve` / `ollama pull llama3.1:8b`                                                                                                                                                                                                        |
| Chat returns `llm_timeout` (Ollama), especially on the Ship 30 essay skill                                                                 | Local 8B models can be slow generating ~1,250 words on CPU; the client timeout may be too tight             | Be patient on first run, or raise the timeout in `OllamaClient.complete`'s `httpx.AsyncClient(timeout=60)`                                                                                                                                        |
| `/health` shows `database: false`                                                                                                          | Wrong `DATABASE_URL`, MySQL not running, or the database doesn't exist yet                                  | Confirm MySQL is running (check in Workbench), confirm the connection string, and run `CREATE DATABASE lenny_growth_assistant CHARACTER SET utf8mb4;` if it hasn't been created                                                                   |
| Backend in Docker can't reach MySQL on your host machine                                                                                   | Using `localhost` in `DATABASE_URL`, which inside a container refers to the container itself, not your host | Use `host.docker.internal` instead of `localhost` (see `.env.example` and `docker-compose.yml` comments)                                                                                                                                          |
| `(2003, "Can't connect to MySQL server...")`                                                                                               | MySQL not listening on the expected host/port, or a firewall/bind-address blocking remote connections       | In MySQL Workbench, confirm the server is running and check `bind-address` in `my.cnf`/`my.ini` isn't restricted to `127.0.0.1` if connecting from Docker                                                                                         |
| `(1045, "Access denied for user...")`                                                                                                      | Wrong username/password, or user lacks privileges on the database                                           | Verify credentials in Workbench; grant privileges: `GRANT ALL PRIVILEGES ON lenny_growth_assistant.* TO 'youruser'@'%';`                                                                                                                          |
| Frontend can't reach backend                                                                                                               | `VITE_API_BASE_URL` mismatch                                                                                | Confirm it points at the backend's actual host:port                                                                                                                                                                                               |
| `pytest` fails on `test_chunker.py` only                                                                                                   | No outbound internet for the `tiktoken` vocab download                                                      | Run once with internet access; it caches afterward                                                                                                                                                                                                |

## Project structure

```text
.
├── backend/            FastAPI app, agent/skills, ingestion, migrations, tests
├── frontend/            React app (chat + artifact viewer)
├── data/transcripts/    Transcript source files (sample transcripts included)
├── agent-transcripts/   Coding-agent session logs (see its README)
├── scripts/setup.sh     One-command native (non-Docker) setup
├── .github/workflows/   CI: backend tests + frontend build on every push
├── docker-compose.yml
├── .env.example
├── PRD.md
├── architecture.md
└── design.md
```

## Continuous integration

`.github/workflows/ci.yml` runs the backend pytest suite and the frontend production build on every push/PR to `main`, so schema, routing, and sanitization regressions are caught before merge, not just at demo time.
