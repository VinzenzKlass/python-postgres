from typing import Any, TypeVar, overload

from psycopg import AsyncCursor
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

from ._operations import exec_query
from .types import Params, Query

T = TypeVar("T", bound=BaseModel)


class Transaction:
    def __init__(self, pool: AsyncConnectionPool[Any], cur: AsyncCursor):
        self._cur = cur
        self._pool = pool

    @overload
    async def __call__(
        self, query: Query, params: Params = (), *, model: type[T], **kwargs: Any
    ) -> list[T]: ...

    @overload
    async def __call__(
        self, query: Query, params: Params = (), **kwargs: Any
    ) -> list[tuple[Any, ...]]: ...

    async def __call__(
        self, query: Query, params: Params = (), model: type[T] | None = None, **kwargs: Any
    ) -> list[T] | list[tuple[Any, ...]]:
        await exec_query(self._pool, self._cur, query, params, **kwargs)
        return (await self._cur.fetchall()) if self._cur.rownumber is not None else []
