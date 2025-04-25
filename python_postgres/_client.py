from contextlib import asynccontextmanager
from typing import AsyncIterator, LiteralString, Optional, Type, TypeVar, overload
from urllib.parse import quote_plus

import psycopg
from psycopg.rows import class_row
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

from ._operations import exec_query, expand_values
from ._transactions import Transaction
from .types import Params, PydanticParams, Query

T = TypeVar("T", bound=BaseModel)


async def _configure(con: psycopg.AsyncConnection) -> None:
    """
    Configure the Connections in the pool.
    """
    await con.set_autocommit(True)


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
        name: str = "python-postgres",
        timeout: float = 30.0,
        max_waiting: int = 0,
        max_lifetime: float = 60 * 60.0,
        max_idle: float = 10 * 60.0,
        reconnect_timeout: float = 5 * 60.0,
    ):
        """
        Initialize the Postgres class to connect to a PostgreSQL database. This will create a
        connection Pool with the given parameters. The connection pool is not opened until the first
        query is executed. This has little performance impact, since you can use the first
        connection while the others are opened in the background and prevents prematurely acquiring
        connections that are not needed.

        :param user: The username to connect to the database.
        :param password: The password for the given user to connect to the database.
        :param host: The host of the database.
        :param port: The port of the database, default is 5432.
        :param database: The database name to connect to, default is `postgres`.
        :param pool_min_size: The minimum number of connections to keep in the pool.
        :param pool_max_size: The maximum number of connections to keep in the pool.
        :param name: An optional name to give to the connection pool, to identify it in the logs.
                     Default to `python-postgres` to distinguish it from other pools that may be
                     active.
        :param timeout: The timeout in seconds to wait for a connection to be acquired from the
                        pool. Default is 30 seconds.
        :param max_waiting: The maximum number of waiting connections to allow. Default is 0, which
                            means no limit.
        :param max_lifetime: The maximum lifetime of a connection in seconds. Default is 60 minutes.
        :param max_idle: The maximum idle time of a connection in seconds. Default is 10 minutes.
        :param reconnect_timeout: The timeout in seconds to wait for a connection to be reconnected
                                    from the pool. Default is 5 minutes.
        """
        self._uri = f"postgresql://{user}:{quote_plus(password)}@{host}:{port}/{database}"
        self._pool = AsyncConnectionPool(
            self._uri,
            min_size=pool_min_size,
            max_size=pool_max_size,
            open=False,
            configure=_configure,
            name=name,
            timeout=timeout,
            max_waiting=max_waiting,
            max_lifetime=max_lifetime,
            max_idle=max_idle,
            reconnect_timeout=reconnect_timeout,
        )
        self.__open = False

    @overload
    async def __call__(
        self, query: Query, params: Params = (), *, model: Type[T], **kwargs
    ) -> list[T] | int: ...

    @overload
    async def __call__(self, query: Query, params: Params = (), **kwargs) -> list[tuple] | int: ...

    async def __call__(
        self,
        query: Query,
        params: Params = (),
        model: Optional[Type[T]] = None,
        **kwargs,
    ) -> list[T] | list[tuple] | int:
        """
        Execute a query and return the results, or the number of affected rows. You can pass any
        query to this method. The Connections in the pool are in `autocommit` mode by default. This
        means that changes to the database are automatically committed and generally is more
        performant. It further allows for Operations that cannot be called in a Transaction like
        `VACUUM` or `CALL`. If you want to execute queries in a Transaction context, use the
        `transaction` method.

        :param query: The query to execute.
        :param params: The parameters to pass to the query.
        :param model: The Pydantic model to parse the results into. If not provided, a new
                      model with all columns in the query will be used.
        :param kwargs: Keyword arguments passed to the Pydantic validation method,
               such as `by_alias`, `exclude`, etc. This is usually the easiest way to
               make sure your model fits the table schema definition.
        :return: The results of the query.
        """
        await self._ensure_open()
        row_factory = class_row(model) if model else None
        async with self._pool.connection() as con:  # type: psycopg.AsyncConnection
            async with con.cursor(binary=True, row_factory=row_factory) as cur:  # type: psycopg.AsyncCursor
                await exec_query(self._pool, cur, query, params)
                return (
                    cur.rowcount
                    if not cur.pgresult or not cur.description or cur.rowcount == 0
                    else await cur.fetchall()
                )

    async def insert(
        self, table_name: LiteralString, params: PydanticParams, prepare: bool = False
    ) -> int:
        """
        Dynamically expand an insert query to correctly handle pydantic models with optional
        fields, applying default values rather than explicitly passing `None` to the query. This
        always produces one single Query. The column names to insert are determined by all the
        non-None across all given models.

        This will not be particularly efficient for large inserts and solves a specific problem. If
        you have uniform models and can construct one query to achieve the same, you should prefer
        that.

        :param table_name: The name of the table to insert into.
        :param params: The Pydantic model or list of models to insert.
        :param prepare: Whether to use prepared statements. Default is False, due to the dynamic
                        nature and possibly rather large size of the query.
        :return: The number of rows inserted.
        """
        if isinstance(params, list) and not params:
            return 0
        await self._ensure_open()
        query, params = expand_values(table_name, params)
        async with self._pool.connection() as con:  # type: psycopg.AsyncConnection
            async with con.cursor(binary=True) as cur:  # type: psycopg.AsyncCursor
                await cur.execute(query, params, prepare=prepare)
                return cur.rowcount

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Transaction]:
        """
        Create a transaction context manager to execute multiple queries in a single transaction.
        You can call the transaction the same way you would call the `Postgres` instance itself.
        """
        await self._ensure_open()
        async with self._pool.connection() as con:  # type: psycopg.AsyncConnection
            async with con.transaction():
                async with con.cursor(binary=True) as cur:  # type: psycopg.AsyncCursor
                    yield Transaction(self._pool, cur)
                    await con.commit()

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[psycopg.AsyncConnection]:
        """
        Acquire a psycopg AsyncConnection from the pool for direct use. **The connection will be in
        autocommit mode by default.**
        """
        await self._ensure_open()
        async with self._pool.connection() as con:  # type: psycopg.AsyncConnection
            yield con

    async def close(self) -> None:
        """
        Close the pool and make it unavailable to new clients.

        All the waiting and future clients will fail to acquire a connection with a PoolClosed
        exception. Currently used connections will not be closed until returned to the pool.

        Wait timeout seconds for threads to terminate their job, if positive. If the timeout
        expires the pool is closed anyway, although it may raise some warnings on exit.
        """
        if self.__open:
            await self._pool.close()
            self.__open = False

    async def _ensure_open(self) -> None:
        if not self.__open:
            await self._pool.open()
            self.__open = True
