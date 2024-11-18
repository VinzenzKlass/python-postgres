from typing import Any

from psycopg import AsyncCursor
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

from ._operations import _exec_query, _pydantic_to_query_and_values, _results
from .types import Params, Query


class Transaction:
    def __init__(self, pool: AsyncConnectionPool, cur: AsyncCursor):
        self._cur = cur
        self._pool = pool

    async def write_pydantic(
        self, table_name: str, model: BaseModel | list[BaseModel], **kwargs
    ) -> int:
        """
        Write a Pydantic model to the database. The model must have the same fields as the table
        in the database.
        :param table_name: The name of the table to write to.
        :param model: The Pydantic model to write to the database.
        :param kwargs: Keyword arguments passed to the Pydantic serialization method,
                       such as `by_alias`, `exclude`, etc. This is usually the easiest way to
                       make sure your model fits the table schema definition.
        :return: The number of rows affected.
        """
        query, values = _pydantic_to_query_and_values(table_name, model, **kwargs)
        return await self.__call__(query, values)

    async def __call__(
        self, query: Query, params: Params = (), **kwargs
    ) -> list[tuple[Any, ...]] | int:
        await _exec_query(self._pool, self._cur, query, params, **kwargs)
        return await _results(self._cur)
