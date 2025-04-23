from itertools import chain
from typing import Type

import psycopg
from psycopg import AsyncCursor, sql
from psycopg.sql import Composed
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

from .exceptions import PGError
from .types import Params, Query, Values


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
        if isinstance(params, Values):
            query, params = _expand_values(query, params)
        elif isinstance(params, BaseModel) or (
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


async def _results(cur: AsyncCursor) -> list[Type[BaseModel] | tuple] | int:
    if not cur.pgresult or not cur.description or cur.rowcount == 0:
        return cur.rowcount
    return await cur.fetchall()


def _expand_values(query: Query, values: Values) -> tuple[Composed, tuple]:
    col_names = (
        list(set(chain.from_iterable(v.model_dump().keys() for v in values.values)))
        if isinstance(values.values, list)
        else values.values.model_dump().keys()
    )
    if not isinstance(values.values, list):
        values = Values([values.values])
    vals, row_sqls = [], []
    for v in values.values:
        placeholders, fields = [], v.model_dump(exclude_none=True)
        for c in col_names:
            if c in fields:
                placeholders.append(sql.Placeholder())
                vals.append(fields[c])
            else:
                placeholders.append(sql.DEFAULT)
        row_sql = sql.SQL("(") + sql.SQL(", ").join(placeholders) + sql.SQL(")")
        row_sqls.append(row_sql)
    values_sql = sql.SQL(", ").join(row_sqls)

    columns_sql = (
        sql.SQL("(") + sql.SQL(", ").join(sql.Identifier(col) for col in col_names) + sql.SQL(")")
    )
    if isinstance(query, str):
        query = sql.SQL(query)

    full_statement = query + columns_sql + sql.SQL(" VALUES ") + values_sql + sql.SQL(";")
    # debug = full_statement.as_string()
    return full_statement, tuple(vals)


def __pydantic_param_to_values(model: BaseModel | list[BaseModel], **kwargs) -> tuple | list[tuple]:
    return (
        [tuple(m.model_dump(**kwargs).values()) for m in model]
        if isinstance(model, list)
        else tuple(model.model_dump(**kwargs).values())
    )
