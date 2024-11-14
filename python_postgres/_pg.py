import asyncio
import re
from contextlib import asynccontextmanager
from typing import AsyncIterator, LiteralString
from urllib.parse import quote_plus

import psycopg
from psycopg.sql import Composed
from psycopg_pool import AsyncConnectionPool

from ._operations import _exec_query, _results
from ._transactions import Transaction
from .exceptions import PGError


class Postgres:
    def __init__(
        self,
        user: str,
        password: str,
        host: str,
        port: int = 5432,
        database: str = "postgres",
        pool_min_size: int = 10,
        pool_max_size: int = 50,
        open_pool: bool = False,
    ):
        self._uri = f"postgresql://{user}:{quote_plus(password)}@{host}:{port}/{database}"
        self._param_pattern = re.compile(r"\$\d+")
        self._pool = _con_pool = AsyncConnectionPool(
            self._uri, min_size=pool_min_size, max_size=pool_max_size, open=open_pool
        )

    async def __call__(
        self, query: LiteralString | Composed, params: tuple | list[tuple] = ()
    ) -> list[tuple] | int:
        try:
            await self.__ensure_pool_open()
            async with self._pool.connection() as con:  # type: psycopg.AsyncConnection
                async with con.cursor(binary=True) as cur:  # type: psycopg.AsyncCursor
                    await _exec_query(self._pool, cur, query, params)
                    await con.commit()
                    return await _results(cur)
        except psycopg.Error as error:
            raise PGError from error

    async def __ensure_pool_open(self):
        if self._pool.closed:
            await self._pool.open()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Transaction]:
        try:
            await self.__ensure_pool_open()
            async with self._pool.connection() as con:  # type: psycopg.AsyncConnection
                async with con.cursor(binary=True) as cur:  # type: psycopg.AsyncCursor
                    yield Transaction(self._pool, cur)
                    await con.commit()
        except psycopg.Error as error:
            raise PGError from error

    async def open(self):
        await self._pool.open()

    async def close(self):
        await self._pool.close()

    def __del__(self):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._pool.close())
            else:
                loop.run_until_complete(self._pool.close())
        except Exception:
            pass
