# Session 02 — Persistence layer migration: Postgres/Supabase → MySQL

Agent: Claude (Anthropic), continuing from session-01. Trigger: the
developer ran into IPv6 connectivity issues reaching Supabase's direct
Postgres host, and had a MySQL server already set up locally (managed via
MySQL Workbench). Rather than keep debugging Supabase network config, the
decision was made to switch the relational persistence layer to MySQL.

## What actually changed
This was **not** a simple `DATABASE_URL` string swap — two things in the
original implementation were genuinely Postgres-specific and needed real
rewrites:

1. **The Alembic migration** (`migrations/versions/0001_initial.py`) used
   `sqlalchemy.dialects.postgresql.UUID` and `.JSONB` directly. These types
   don't exist for MySQL and had to be replaced with `CHAR(36)` (MySQL has
   no native UUID column type) and MySQL's native `JSON` type, plus
   `mysql_engine="InnoDB"` / `mysql_charset="utf8mb4"` table options that
   have no Postgres equivalent.
2. **The portable `UUID` TypeDecorator** in `app/db/models.py` originally
   branched on `dialect.name == "postgresql"` to use a native UUID column,
   falling back to `CHAR(36)` otherwise. Since MySQL also has no native UUID
   type, this branch was dead weight for the new target — simplified to
   always use `CHAR(36)`, which is actually *less* code than before.

Everything else in the app (routes, skills, retrieval, agent routing) was
already database-agnostic by design, since all of it talks to the ORM layer
and never touches SQL directly — so the migration only touched
`app/db/`, `migrations/`, `app/config.py`, `app/api/routes_chat.py`, and
`docker-compose.yml`/`.env.example`.

## Failed attempt and correction

### `now()` as a DDL default is not universally valid MySQL
**What happened:** The first draft of the rewritten migration used
`server_default=sa.func.now()` for `created_at`/`updated_at`, mirroring the
original Postgres migration. Dry-running it in Alembic's offline SQL mode
(`alembic upgrade head --sql`) against the MySQL dialect rendered
`DEFAULT now()` as a literal function call in the DDL.
**Why this is a problem:** MySQL only allows arbitrary expression defaults
(like a bare function call) for `DATETIME`/`TIMESTAMP` columns starting in
MySQL 8.0.13; MariaDB and older MySQL versions require the literal keyword
`CURRENT_TIMESTAMP` instead. Shipping `now()` as the default would work on
a recent MySQL 8 install but silently fail on an older MySQL or MariaDB
target — exactly the kind of environment-dependent bug that's easy to miss
if you only test against whatever happens to be on your own machine.
**How it was caught:** Ran the migration in Alembic's `--sql` (offline)
mode specifically to eyeball the generated DDL before assuming it was
correct — this doesn't require a live database connection, so it's a cheap
check to run before ever pointing the migration at a real server.
**Fix:** Replaced `sa.func.now()` with `sa.text("CURRENT_TIMESTAMP")` for
every `server_default` in the migration — valid across MySQL 5.7, MySQL
8.x, and MariaDB.

## Also fixed while in the neighborhood
- `app/api/routes_chat.py` was writing `datetime.now(timezone.utc)` (a
  timezone-aware datetime) into `session.updated_at`. MySQL's `DATETIME`
  column has no timezone concept, and binding a tz-aware Python datetime
  through PyMySQL/aiomysql risks producing an invalid literal. Changed to
  `.replace(tzinfo=None)` before assignment so a naive UTC datetime is
  always what gets bound.
- Dropped `timezone=True` from every `DateTime` column definition in
  `app/db/models.py` — it was a no-op holdover from the Postgres version
  (MySQL doesn't support timezone-aware storage either way) and left in
  would have been misleading to a future reader.
- `app/db/database.py`: added `pool_recycle=3600` to the non-SQLite engine
  kwargs. MySQL's default `wait_timeout` closes idle connections after 8
  hours; without `pool_recycle`, a long-idle pooled connection can be
  killed server-side and surface as "MySQL server has gone away" on the
  next request. `pool_pre_ping` alone catches this reactively; recycling
  proactively avoids hitting it as often.

## Verification performed this session
- `pytest -q` — 21/21 tests still passing (SQLite-backed test suite is
  unaffected by the backend DB swap, by design — that was the whole point
  of the portable `UUID` type).
- `alembic upgrade head --sql` against `mysql+aiomysql://...` — confirmed
  valid MySQL DDL end to end, including correct auto-backtick-quoting of
  `role` (a MySQL reserved word) by Alembic's compiler, correct foreign
  keys with `ON DELETE CASCADE` / `ON DELETE SET NULL`, and correct
  `CURRENT_TIMESTAMP` defaults after the fix above.
- `python -m py_compile` across all touched files.

## What a reviewer should sanity-check on a real MySQL instance
This session validated the migration's generated SQL offline (no live
MySQL server was available in the build environment). Before treating this
as fully verified, run `alembic upgrade head` against a real MySQL
instance and confirm:
- Foreign key constraints with `ON DELETE CASCADE`/`SET NULL` actually
  enforce as expected (requires the `innodb` storage engine, which is set
  explicitly, but worth confirming on the target server's default
  configuration).
- `utf8mb4` is actually the server/database default, or that the explicit
  `mysql_charset="utf8mb4"` table option is respected — some MySQL hosts
  restrict schema-level charset overrides.
