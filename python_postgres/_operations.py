from typing import Any

import psycopg
from psycopg import AsyncCursor
from psycopg_pool import AsyncConnectionPool

from .exceptions import PGError
from .types import Params, Query


async def _exec_query(
    pool: AsyncConnectionPool,
    cur: AsyncCursor,
    query: Query,
    params: Params,
    is_retry: bool = False,
) -> None:
    try:
        if not params:
            await cur.execute(query)
            return
        if isinstance(params, list):
            await cur.executemany(query, params)
            return
        await cur.execute(query, params)
    except psycopg.OperationalError as error:
        if is_retry:
            raise PGError from error
        await pool.check()
        await _exec_query(pool, cur, query, params, True)


async def _results(cur: AsyncCursor) -> list[tuple[Any, ...]] | int:
    return await cur.fetchall() if cur.pgresult and cur.pgresult.ntuples > 0 else cur.rowcount
