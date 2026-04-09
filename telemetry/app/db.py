"""Optional asyncpg pool when DATABASE_URL is set."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_pool = None


async def init_db_pool() -> None:
    global _pool
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        _pool = None
        logger.info("DATABASE_URL unset — catalog DB checks skipped (legacy ingest).")
        return
    import asyncpg

    try:
        _pool = await asyncpg.create_pool(url, min_size=1, max_size=5)
    except Exception:
        logger.exception("Failed to connect DATABASE_URL — running without catalog DB.")
        _pool = None
        return
    logger.info("DATABASE_URL connected — catalog + system_catalog_configs active for ingest.")


async def close_db_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def db_pool():
    return _pool
