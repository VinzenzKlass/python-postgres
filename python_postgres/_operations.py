import datetime
from itertools import chain
from typing import Type

import psycopg
from psycopg import AsyncCursor, sql
from psycopg.sql import Composed
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, Field, create_model

from ._adapters import Values
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


async def _results(cur: AsyncCursor, model: Type[BaseModel] = None) -> list[Type[BaseModel]] | int:
    if not cur.pgresult or not cur.description or cur.rowcount == 0:
        return cur.rowcount
    cols = {
        col.name: (__pg_types(col.type_display) | None, Field(default=None))
        for col in cur.description
    }
    col_names = cols.keys()
    model = model or create_model("Result", **cols)
    return [
        model.model_validate(dict(zip(col_names, row, strict=True))) for row in await cur.fetchall()
    ]


def _expand_values(query: Query, values: Values) -> tuple[Composed, list[tuple]]:
    col_names = (
        list(set(chain.from_iterable(v.model_dump().keys() for v in values.values)))
        if isinstance(values.values, list)
        else values.values.model_dump().keys()
    )
    val_stmt = (
        sql.SQL(" (")
        + sql.SQL(", ").join(sql.Identifier(col) for col in col_names)
        + sql.SQL(")")
        + sql.SQL(" VALUES (")
        + sql.SQL(", ").join(sql.Placeholder() for _ in col_names)
        + sql.SQL(");")
    )
    vals: list[tuple] = []
    if isinstance(values.values, list):
        for v in values.values:
            row_vals, fields = [], v.model_dump(exclude_none=True)
            for c in col_names:
                row_vals.append(fields.get(c, "DEFAULT"))
            vals.append(tuple(row_vals))
    else:
        row_vals, fields = [], values.values.model_dump(exclude_none=True)
        for c in col_names:
            row_vals.append(fields.get(c, "DEFAULT"))
        vals.append(tuple(row_vals))
    if isinstance(query, str):
        query = sql.SQL(query)
    full_statement: Composed = query + val_stmt
    # debug = full_statement.as_string()
    return full_statement, vals


def __pydantic_param_to_values(model: BaseModel | list[BaseModel], **kwargs) -> tuple | list[tuple]:
    return (
        [tuple(m.model_dump(**kwargs).values()) for m in model]
        if isinstance(model, list)
        else tuple(model.model_dump(**kwargs).values())
    )


def __pg_types(raw: str) -> Type:
    if "datetime" in raw or "timestamp" in raw:
        return datetime.datetime
    if "date" in raw:
        return datetime.date
    if "json" in raw:
        return dict
    if "int" in raw:
        return int
    if "bool" in raw:
        return bool
    if "float" in raw:
        return float
    if "numeric" in raw:
        return float
    if "double" in raw:
        return float
    return str
