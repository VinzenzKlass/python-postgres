from psycopg import AsyncCursor
from psycopg_pool import AsyncConnectionPool

from ._operations import _exec_query
from .types import Params, Query


class Transaction:
    def __init__(self, pool: AsyncConnectionPool, cur: AsyncCursor):
        self._cur = cur
        self._pool = pool

    async def __call__(self, query: Query, params: Params = ()) -> None:
        await _exec_query(self._pool, self._cur, query, params)
