# The Lenny Growth Assistant

A grounded conversational assistant over Lenny's Podcast transcripts, with a
Ship 30 for 30 essay skill, Markdown/HTML artifact generation, and a
sandboxed in-app Artifact Viewer.

See also: [`PRD.md`](./PRD.md) (discovery brief, scope, acceptance criteria),
[`architecture.md`](./architecture.md) (schema, API, retrieval flow,
security), [`design.md`](./design.md) (UI/UX principles),
[`DEMO_SCRIPT.md`](./DEMO_SCRIPT.md) (talking points/checklist for the demo
video), [`agent-transcripts/`](./agent-transcripts) (build session log,
including failed attempts and fixes).

## Architecture at a glance
- **Backend**: FastAPI, async SQLAlchemy → MySQL, FAISS vector
  store, Groq (cloud) / Ollama (local) behind one LLM interface.
- **Frontend**: React (Vite), sandboxed iframe Artifact Viewer.
- **Skills**: `grounded_qa` (default), `ship30` (essay generation),
  `artifact` (Markdown/HTML generation), dispatched by a rule-based router.

## Prerequisites
- Docker + Docker Compose (recommended path), **or** Python 3.11+ and
  Node 20+ for running services natively.
- A running MySQL server (e.g. managed via MySQL Workbench) reachable from
  wherever the backend runs, for `DATABASE_URL`.
- A free [Groq API key](https://console.groq.com/keys) for the cloud
  provider.
- [Ollama](https://ollama.com) installed locally — **mandatory for the
  demo** per the assignment brief.

## Quickstart (Docker Compose)

```bash
git clone <this-repo>
cd lenny-growth-assistant
cp .env.example .env
# edit .env: set DATABASE_URL (MySQL) and GROQ_API_KEY

docker compose up --build
# pull the local model once the ollama container is up:
docker compose exec ollama ollama pull llama3.1:8b
```

Then, in a separate terminal, run ingestion once so the assistant has
something to retrieve from (sample transcripts are included so this works
out of the box). Database migrations run automatically on container start
via `entrypoint.sh` (`alembic upgrade head`), so no manual migration step is
needed with Docker Compose:

```bash
docker compose exec backend python -m app.ingestion.ingest_transcripts
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000 (docs at `/docs`)
- Health check: http://localhost:8000/health

## Running natively (without Docker)

The fastest path is the setup script, which creates `.env`, sets up the
backend venv, runs migrations, ingests the sample transcripts, and installs
frontend dependencies in one go:

```bash
./scripts/setup.sh
```

Or step by step:

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # edit as needed; loaded from repo root
alembic upgrade head
python -m app.ingestion.ingest_transcripts
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

**Ollama** (separately)
```bash
ollama serve
ollama pull llama3.1:8b
```

## Switching LLM providers
Set `LLM_PROVIDER=groq` or `LLM_PROVIDER=ollama` in `.env` (server-wide
default), or use the toggle in the top bar of the UI to override it per
session/request — no code changes required either way. `/health` reports
whether the currently configured provider (and Ollama specifically) is
reachable.

## Environment variables

See [`.env.example`](./.env.example) for the full list with defaults. Key
required variables:

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | Yes | MySQL connection string (async, `mysql+aiomysql://...`) |
| `GROQ_API_KEY` | Only if using `LLM_PROVIDER=groq` | Cloud inference |
| `LLM_PROVIDER` | No (default `groq`) | `groq` \| `ollama` |
| `OLLAMA_BASE_URL` | No (default `http://localhost:11434`) | Local inference endpoint |
| `FAISS_INDEX_DIR` | No | Where the vector index is written/read |

Never commit a filled-in `.env` — only `.env.example` is checked in.

## Tests

**Backend** (21 automated tests: health, skill routing, transcript chunking,
artifact HTML sanitization, session persistence via isolated in-memory
SQLite, RAG grounding-threshold logic, and full `/chat` endpoint flows with
a mocked LLM — routing, persistence, citations, auto-titling, and error
propagation):
```bash
cd backend
pytest -q
```
> Note: `test_chunker.py` downloads a tokenizer vocabulary file on first run
> (`tiktoken`); it needs outbound internet access once, then caches locally.

**Manual UI test plan** (run after `docker compose up`):
1. Create a new chat → ask a question covered by the sample transcripts →
   confirm the answer cites `sample-plg-pricing-episode` or
   `sample-onboarding-activation-episode`.
2. Ask a follow-up question ("what about for enterprise?") → confirm the
   assistant uses prior context, not just the latest message.
3. Ask something clearly outside the corpus (e.g. "what's the weather
   today?") → confirm the response acknowledges insufficient material rather
   than inventing an answer, and shows the low-confidence warning.
4. Say "turn that into a Ship 30 for 30 essay" → confirm ~1,250 words,
   headings, bullets, bold emphasis, and a specific takeaway.
5. Say "generate an HTML artifact summarizing this" → confirm the Artifact
   Viewer opens beside the chat and renders correctly.
6. Refresh the page → confirm the session and its messages reload from
   persistence.
7. Toggle Groq ↔ Ollama → send a message on each → confirm the response
   shows the expected provider and the status pills update.
8. Stop the Ollama container/process → send a message on Ollama → confirm a
   specific, actionable error banner (not a generic failure).
9. Delete a session → confirm it disappears from the sidebar and its
   messages/artifacts are gone.

## Production readiness

**Filling in `.env` makes this runnable — it does not make it
production-ready.** Those are different bars, and this project deliberately
targets the first one (a working, demoable, well-architected v1) rather than
overclaiming the second. Below is an honest accounting of what's already in
place versus what a real production rollout would still need.

### Already production-grade
- Async FastAPI + SQLAlchemy throughout, no blocking calls in request paths.
- Schema managed by Alembic migrations (not ad-hoc `create_all()`), with a
  matching MySQL/SQLite-portable `UUID` type.
- Typed error handling (`AppError` subclasses → consistent JSON shape) and
  structured logging at every skill/provider/DB boundary.
- Config-driven LLM provider switching (no code changes to go
  cloud ↔ local).
- Layered artifact-rendering security (prompt constraints → server-side
  sanitization → non-scripting sandboxed iframe) — see `architecture.md`.
- CI (`.github/workflows/ci.yml`) running tests + a frontend build on every
  push, so regressions are caught pre-merge.
- Graceful degradation: `/health` reports DB/FAISS/LLM reachability
  independently rather than crashing; missing optional dependencies
  (e.g. the embedding model) don't take down unrelated routes.

### Gaps to close before real production use
| Gap | Why it matters | What closing it looks like |
|---|---|---|
| **No authentication** | `user_id` is a free-text string anyone can spoof — no login, no enforced session ownership. | Add real auth (an auth provider like Clerk/Auth0, or your own IdP) and scope every query by the authenticated user, not a client-supplied string. |
| **No rate limiting** | Nothing stops abusive or buggy clients from hammering Groq or the DB. | Add per-user/IP rate limiting at the API gateway or in FastAPI middleware (e.g. `slowapi`). |
| **CORS defaults to localhost** | `CORS_ORIGINS` in `.env.example` is a dev default. | Set it to your real frontend origin(s) only — never a wildcard — in production `.env`. |
| **No TLS termination** | Docker Compose serves plain HTTP. | Put a reverse proxy (nginx/Caddy) in front, or rely on your host's TLS (Railway, Fly.io, Vercel, etc. handle this automatically). |
| **`SESSION_SECRET` is unused** | It exists in config but nothing signs cookies/tokens with it yet — dead config today. | Wire it into real session/auth token signing once auth is added, or remove it if auth is handled entirely by a third party. |
| **`.env` as the only secrets story** | Fine for a demo; risky as the sole mechanism long-term. | Move secrets to your platform's secret manager (your host's env/secrets settings, AWS Secrets Manager, etc.) instead of a file on disk. |
| **No monitoring/alerting** | Structured logs exist but go nowhere — an outage is only visible if someone is watching the terminal. | Ship logs to an aggregator (e.g. Better Stack, Datadog) and add uptime/error-rate alerting (e.g. Sentry for exceptions). |
| **No load testing** | The FAISS index is a single in-process flat index with no concurrency tuning; untested under real traffic. | Load-test with a tool like `locust` or `k6`, and re-evaluate the ANN-vs-flat-index trade-off if the corpus or QPS grows. |
| **No backup/retention policy** | No automated backups configured for the MySQL instance, and there's no data-deletion story. | Configure scheduled `mysqldump`/binlog-based backups (or use a managed MySQL host with automated backups); add a deletion/export flow if this ever touches real user data (GDPR-style requests). |
| **Groq free tier** | Rate-limited, not intended for production load. | Move to a paid tier, or add a second cloud provider as a fallback behind the same `LLMClient` interface. |
| **Single backend instance / single MySQL instance** | No horizontal scaling or DB replication configured, though the app is already close to stateless (all state lives in MySQL/FAISS-on-disk). | Run multiple backend replicas behind a load balancer; add MySQL read replicas or move to a managed MySQL host (e.g. PlanetScale, RDS) for HA; move the FAISS index to shared/networked storage so replicas stay in sync. |

None of these are surprises — they're the standard gap between "a
well-architected v1" and "a production system," and the architecture here
(stateless-by-design backend, config-driven providers, typed errors) was
built specifically to make closing them additive rather than requiring a
rewrite.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/health` shows `faiss_index_loaded: false` | Ingestion hasn't run yet | `python -m app.ingestion.ingest_transcripts` |
| Chat returns `retrieval_index_missing` | Same as above | Same as above |
| `alembic upgrade head` fails with "table already exists" | Tables were created manually outside Alembic | Drop the tables in MySQL Workbench, or `alembic stamp head` if the schema already matches |
| Chat returns `llm_provider_unavailable` (Groq) | Missing/invalid `GROQ_API_KEY` | Set it in `.env`, restart backend |
| Chat returns `llm_provider_unavailable` (Ollama) | `ollama serve` not running, or model not pulled | `ollama serve` / `ollama pull llama3.1:8b` |
| `/health` shows `database: false` | Wrong `DATABASE_URL`, MySQL not running, or the database doesn't exist yet | Confirm MySQL is running (check in Workbench), confirm the connection string, and run `CREATE DATABASE lenny_growth_assistant CHARACTER SET utf8mb4;` if it hasn't been created |
| Backend in Docker can't reach MySQL on your host machine | Using `localhost` in `DATABASE_URL`, which inside a container refers to the container itself, not your host | Use `host.docker.internal` instead of `localhost` (see `.env.example` and `docker-compose.yml` comments) |
| `(2003, "Can't connect to MySQL server...")` | MySQL not listening on the expected host/port, or a firewall/bind-address blocking remote connections | In MySQL Workbench, confirm the server is running and check `bind-address` in `my.cnf`/`my.ini` isn't restricted to `127.0.0.1` if connecting from Docker |
| `(1045, "Access denied for user...")` | Wrong username/password, or user lacks privileges on the database | Verify credentials in Workbench; grant privileges: `GRANT ALL PRIVILEGES ON lenny_growth_assistant.* TO 'youruser'@'%';` |
| Frontend can't reach backend | `VITE_API_BASE_URL` mismatch | Confirm it points at the backend's actual host:port |
| `pytest` fails on `test_chunker.py` only | No outbound internet for the `tiktoken` vocab download | Run once with internet access; it caches afterward |

## Project structure
```
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
`.github/workflows/ci.yml` runs the backend pytest suite and the frontend
production build on every push/PR to `main`, so schema, routing, and
sanitization regressions are caught before merge, not just at demo time.
