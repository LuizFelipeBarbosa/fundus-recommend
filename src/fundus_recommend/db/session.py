import ssl
from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from fundus_recommend.config import settings


def _async_url_and_connect_args() -> tuple[str, dict]:
    """Strip sslmode/channel_binding from the URL (asyncpg doesn't accept them) and pass SSL via connect_args."""
    url = settings.database_url
    if "sslmode=require" in url:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        # Remove params that asyncpg doesn't accept as URL/keyword args
        for param in ["sslmode=require", "channel_binding=require"]:
            url = url.replace(f"?{param}&", "?").replace(f"&{param}", "").replace(f"?{param}", "")
        return url, {"ssl": ctx}
    return url, {}


_async_url, _async_connect_args = _async_url_and_connect_args()

# Async engine for FastAPI
async_engine = create_async_engine(
    _async_url, echo=False, connect_args=_async_connect_args,
    pool_size=5, max_overflow=10, pool_pre_ping=True, pool_recycle=300,
)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine for CLI crawl/embed commands
sync_engine = create_engine(settings.database_url_sync, echo=False)
SyncSessionLocal = sessionmaker(sync_engine, class_=Session, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
