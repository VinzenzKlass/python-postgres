from contextlib import asynccontextmanager
from typing import AsyncIterator, Type, TypeVar
from urllib.parse import quote_plus

import psycopg
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

from ._operations import _exec_query, _results
from ._transactions import Transaction
from .exceptions import PGError
from .types import Params, Query

T = TypeVar("T", bound=BaseModel)


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
    ):
        """
        Initialize the Postgres class to connect to a PostgreSQL database.
        :param user: The username to connect to the database.
        :param password: The password for the given user to connect to the database.
        :param host: The host of the database.
        :param port: The port of the database, default is 5432.
        :param database: The database name to connect to, default is `postgres`.
        :param pool_min_size: The minimum number of connections to keep in the pool.
        :param pool_max_size: The maximum number of connections to keep in the pool.
        """
        self._uri = f"postgresql://{user}:{quote_plus(password)}@{host}:{port}/{database}"
        self._pool = AsyncConnectionPool(
            self._uri, min_size=pool_min_size, max_size=pool_max_size, open=False
        )
        self.__open = False

    async def __call__(
        self, query: Query, params: Params = (), model: Type[T] = None, **kwargs
    ) -> list[T] | int:
        """
        Execute a query and return the results. Check the `psycopg` documentation for more
        information.
        :param query:  The query to execute.
        :param params: The parameters to pass to the query.
        :param model: The Pydantic model to serialize the results into. If not provided, a new
                      model with all columns in the query will be used.
        :param kwargs: Keyword arguments passed to the Pydantic serialization method,
               such as `by_alias`, `exclude`, etc. This is usually the easiest way to
               make sure your model fits the table schema definition.#
        :return: The results of the query.
        """
        try:
            if not self.__open:
                await self._pool.open()
                self.__open = True
            async with self._pool.connection() as con:  # type: psycopg.AsyncConnection
                async with con.cursor(binary=True) as cur:  # type: psycopg.AsyncCursor
                    await _exec_query(self._pool, cur, query, params)
                    await con.commit()
                    return await _results(cur, model)
        except psycopg.Error as error:
            raise PGError from error

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Transaction]:
        """
        Create a transaction context manager to execute multiple queries in a single transaction.
        You can call the transaction the same way you would call the `Postgres` instance itself.
        """
        try:
            async with self._pool.connection() as con:  # type: psycopg.AsyncConnection
                async with con.cursor(binary=True) as cur:  # type: psycopg.AsyncCursor
                    yield Transaction(self._pool, cur)
                    await con.commit()
        except psycopg.Error as error:
            raise PGError from error
