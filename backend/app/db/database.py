from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


def _patch_aiomysql_ping() -> None:
    """Workaround for a SQLAlchemy 2.0.35 + aiomysql 0.2.0 incompatibility:
    SQLAlchemy's do_ping() calls dbapi_connection.ping() with no arguments,
    but aiomysql's async connection wrapper requires `reconnect` to be
    passed explicitly, raising:
    "AsyncAdapt_aiomysql_connection.ping() missing 1 required positional
    argument: 'reconnect'" on every connection checkout. This patches the
    method to default `reconnect=True` when called with no args, which
    also lets pool_pre_ping actually work for MySQL."""
    try:
        from sqlalchemy.dialects.mysql.aiomysql import AsyncAdapt_aiomysql_connection

        original_ping = AsyncAdapt_aiomysql_connection.ping

        def patched_ping(self, *args, **kwargs):
            if not args and "reconnect" not in kwargs:
                kwargs["reconnect"] = True
            return original_ping(self, *args, **kwargs)

        AsyncAdapt_aiomysql_connection.ping = patched_ping
    except ImportError:
        pass


_patch_aiomysql_ping()

settings = get_settings()

# pool_pre_ping guards against MySQL closing idle connections underneath us
# (MySQL's default wait_timeout closes idle connections after 8h; pre_ping
# detects and transparently replaces a dead connection instead of raising
# "MySQL server has gone away"). pool_recycle proactively recycles
# connections before that timeout is likely to hit. Pool-size kwargs are
# only valid for MySQL/asyncmy's QueuePool; SQLite (used only in the
# unit-test suite via a dependency override) uses StaticPool and rejects
# them, so they're applied conditionally.
_engine_kwargs = {"echo": False}
if not settings.database_url.startswith("sqlite"):
    # pool_pre_ping is safe now that _patch_aiomysql_ping() above fixes the
    # aiomysql ping() signature mismatch (see that function's docstring).
    _engine_kwargs.update(
        pool_size=5,
        max_overflow=5,
        pool_recycle=1800,
        pool_pre_ping=True,
        connect_args={"charset": "utf8mb4"},
    )
else:
    _engine_kwargs["pool_pre_ping"] = True  # safe and useful for SQLite in the test suite

engine = create_async_engine(settings.database_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """Used by /health to report DB reachability without crashing the app."""
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
