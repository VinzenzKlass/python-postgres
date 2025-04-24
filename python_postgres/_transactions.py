from typing import Type, TypeVar, overload

from psycopg import AsyncCursor
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

from ._operations import exec_query, results
from .types import Params, Query

T = TypeVar("T", bound=BaseModel)


class Transaction:
    def __init__(self, pool: AsyncConnectionPool, cur: AsyncCursor):
        self._cur = cur
        self._pool = pool

    @overload
    async def __call__(
        self, query: Query, params: Params = (), *, model: Type[T], **kwargs
    ) -> list[T] | int: ...

    @overload
    async def __call__(self, query: Query, params: Params = (), **kwargs) -> list[tuple] | int: ...

    async def __call__(
        self, query: Query, params: Params = (), model: Type[T] = None, **kwargs
    ) -> list[T | tuple] | int:
        await exec_query(self._pool, self._cur, query, params, **kwargs)
        return await results(self._cur)
