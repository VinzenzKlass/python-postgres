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

    models, col_names, row_sqls, row_values = [], set(), [], []
    for v in values:
        m_dict = v.model_dump(exclude_none=True)
        models.append(m_dict)
        col_names.update(m_dict.keys())

    for model in models:
        placeholders, row = [], []
        for c in col_names:
            if c in model:
                placeholders.append(sql.Placeholder())
                row.append(model[c])
            else:
                placeholders.append(sql.DEFAULT)
        row_sqls.append(sql.SQL("(") + sql.SQL(", ").join(placeholders) + sql.SQL(")"))
        row_values.extend(row)
    columns_sql = (
        sql.SQL("(") + sql.SQL(", ").join(sql.Identifier(col) for col in col_names) + sql.SQL(")")
    )
    full_statement = query + columns_sql + sql.SQL("VALUES") + sql.SQL(", ").join(row_sqls)
    # debug = full_statement.as_string()
    return full_statement, tuple(row_values)


def __pydantic_param_to_values(model: BaseModel | list[BaseModel], **kwargs) -> tuple | list[tuple]:
    # TODO: This would probably be better suited as a psycopg Dumper.
    return (
        [tuple(m.model_dump(**kwargs).values()) for m in model]
        if isinstance(model, list)
        else tuple(model.model_dump(**kwargs).values())
    )
