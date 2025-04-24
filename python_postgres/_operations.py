from typing import LiteralString, Type

import psycopg
from psycopg import AsyncCursor, sql
from psycopg.sql import Composed
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

from .types import Params, PydanticParams, Query


async def exec_query(
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
            raise error
        await pool.check()
        await exec_query(pool, cur, query, params, True)


async def results(cur: AsyncCursor) -> list[Type[BaseModel] | tuple] | int:
    if not cur.pgresult or not cur.description or cur.rowcount == 0:
        return cur.rowcount
    return await cur.fetchall()


def expand_values(table_name: LiteralString, values: PydanticParams) -> tuple[Composed, tuple]:
    query = sql.SQL("INSERT INTO ") + sql.Identifier(table_name)
    if isinstance(values, BaseModel):
        raw = values.model_dump(exclude_none=True)
        vals = tuple(raw.values())
        return query + sql.SQL("(") + sql.SQL(", ").join(
            sql.Identifier(k) for k in raw.keys()
        ) + sql.SQL(")") + sql.SQL("VALUES") + sql.SQL("(") + sql.SQL(", ").join(
            sql.Placeholder() for _ in range(len(vals))
        ) + sql.SQL(")"), vals

    col_names = set()
    processed_values = []
    for val in values:
        fields = val.model_dump(exclude_none=True)
        col_names.update(fields.keys())
        processed_values.append(fields)

    vals, row_sqls = [], []
    for v in values:
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
    full_statement = query + columns_sql + sql.SQL(" VALUES ") + values_sql + sql.SQL(";")
    # debug = full_statement.as_string()
    return full_statement, tuple(vals)


def __pydantic_param_to_values(model: BaseModel | list[BaseModel], **kwargs) -> tuple | list[tuple]:
    # TODO: This would probably be better suited as a psycopg Dumper.
    return (
        [tuple(m.model_dump(**kwargs).values()) for m in model]
        if isinstance(model, list)
        else tuple(model.model_dump(**kwargs).values())
    )
