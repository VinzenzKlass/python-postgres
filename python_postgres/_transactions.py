from psycopg import AsyncCursor
from psycopg_pool import AsyncConnectionPool

from ._operations import _exec_query, _results
from .types import Params, Query


class Transaction:
    def __init__(self, pool: AsyncConnectionPool, cur: AsyncCursor):
        self._cur = cur
        self._pool = pool

    async def __call__(self, query: Query, params: Params = (), **kwargs) -> list[tuple] | int:
        await _exec_query(self._pool, self._cur, query, params, **kwargs)
        return await _results(self._cur)
