from typing import LiteralString

from psycopg import AsyncCursor
from psycopg.sql import Composed
from psycopg_pool import AsyncConnectionPool

from postgresql._operations import _exec_query


class Transaction:
    def __init__(self, pool: AsyncConnectionPool, cur: AsyncCursor):
        self._cur = cur
        self._pool = pool

    async def __call__(self, query: LiteralString | Composed, params: tuple | list[tuple] = ()):
        await _exec_query(self._pool, self._cur, query, params)
