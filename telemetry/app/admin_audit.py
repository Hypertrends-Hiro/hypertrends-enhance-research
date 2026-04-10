"""Best-effort audit rows for admin mutations."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def log_admin_request(
    pool: Any,
    *,
    method: str,
    path: str,
    actor_label: str,
    request_summary: dict[str, Any],
) -> None:
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO telemetry_admin_audit (method, path, actor_label, request_summary)
                VALUES ($1, $2, $3, $4::jsonb)
                """,
                method,
                path,
                actor_label[:256],
                json.dumps(request_summary, default=str),
            )
    except Exception:
        logger.warning("telemetry_admin_audit insert failed (run sql/003?)", exc_info=True)
