from typing import Any, Collection

import psycopg
from psycopg import AsyncCursor, sql
from psycopg.sql import Composed
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

from .exceptions import PGError
from .types import Params, Query


async def _exec_query(
    pool: AsyncConnectionPool,
    cur: AsyncCursor,
    query: Query,
    params: Params,
    is_retry: bool = False,
    **kwargs,
) -> None:
    try:
        if not params:
            await cur.execute(query)
            return
        if isinstance(params, BaseModel) or (
            isinstance(params, list) and isinstance(params[0], BaseModel)
        ):
            params = __pydantic_param_to_values(params, **kwargs)
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


def _pydantic_to_query_and_values(
    table_name: str, model: BaseModel | list[BaseModel], **kwargs
) -> tuple[Composed, tuple | list[tuple]]:
    if isinstance(model, list):
        fields = model[0].model_dump(**kwargs).keys()
        return (
            __to_composed(table_name, fields),
            [tuple(m.model_dump(**kwargs).values()) for m in model],
        )

    m = model.model_dump(**kwargs)
    return __to_composed(table_name, m.keys()), tuple(m.values())


def __pydantic_param_to_values(model: BaseModel | list[BaseModel], **kwargs) -> tuple | list[tuple]:
    return (
        [tuple(m.model_dump(**kwargs).values()) for m in model]
        if isinstance(model, list)
        else tuple(model.model_dump(**kwargs).values())
    )


def __to_composed(table_name: str, fields: Collection[str]) -> Composed:
    return sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table_name),
        sql.SQL(",").join(map(sql.Identifier, fields)),
        sql.SQL(",").join(sql.Placeholder() * len(fields)),
    )
