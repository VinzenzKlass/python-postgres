import datetime
from typing import Type

import psycopg
from psycopg import AsyncCursor
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, create_model

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


async def _results(cur: AsyncCursor, model: Type[BaseModel] = None) -> list[Type[BaseModel]] | int:
    cols = {col.name: __pg_types(col.type_display) for col in cur.description}
    model = model or create_model("Result", **cols)
    col_names = cols.keys()
    return (
        [model(**dict(zip(col_names, row, strict=True))) for row in await cur.fetchall()]
        if cur.pgresult and cur.pgresult.ntuples > 0
        else cur.rowcount
    )


def __pydantic_param_to_values(model: BaseModel | list[BaseModel], **kwargs) -> tuple | list[tuple]:
    return (
        [tuple(m.model_dump(**kwargs).values()) for m in model]
        if isinstance(model, list)
        else tuple(model.model_dump(**kwargs).values())
    )


def __pg_types(raw: str) -> Type:
    if "date" in raw:
        return datetime.date
    if "int" in raw:
        return int
    if "bool" in raw:
        return bool
    if "float" in raw:
        return float
    if "double" in raw:
        return float
    return str
