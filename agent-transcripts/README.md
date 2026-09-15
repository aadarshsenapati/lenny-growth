# Agent transcripts

Per the assignment's deliverable #6, this folder should contain the raw
coding-agent session logs used while building this project -- including
failed attempts and how they were corrected -- with all secrets and API
keys removed before committing.

## How to populate this folder

- If you used Claude Code: export the session transcript (or copy the
  relevant terminal/chat log) into `agent-transcripts/session-01.md`,
  `session-02.md`, etc., one file per work session.
- If you used Cursor/Codex/Devin: use their session export/history feature,
  or copy paste the conversation into a markdown file here.
- Before committing, grep for and remove: API keys, database connection
  strings, tokens, and any personal data pasted into the session.
- Include at least one example of a failed attempt and the fix, e.g.:
  "Agent generated a synchronous SQLAlchemy session in an async FastAPI
  route, causing a runtime error under load -- corrected by switching to
  AsyncSession + an async driver throughout db/database.py."

## Suggested structure

```
agent-transcripts/
  session-01-build-log.md              (backend, RAG, agent layer, frontend scaffold)
  session-02-mysql-migration.md        (Postgres -> MySQL persistence swap)
  session-03-...
```
