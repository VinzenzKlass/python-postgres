from typing import Any, LiteralString, Optional

import psycopg
from psycopg import AsyncCursor, sql
from psycopg.rows import TupleRow
from psycopg.sql import Composed
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

from .types import Params, PydanticParams, Query


async def exec_query(
    pool: AsyncConnectionPool[Any],
    cur: AsyncCursor[TupleRow] | AsyncCursor[BaseModel],
    query: Query,
    params: Params,
    is_retry: bool = False,
    **kwargs: Any,
) -> None:
    try:
        if not params:
            await cur.execute(query)
            return
        parsed_params: tuple[Any, ...] | list[tuple[Any, ...]]
        if isinstance(params, BaseModel):
            parsed_params = _model_to_values(params, **kwargs)
        elif isinstance(params, list) and isinstance(params[0], BaseModel):
            parsed_params = [_model_to_values(m, **kwargs) for m in params]  # pyright: ignore[reportArgumentType] # noqa
        else:
            parsed_params = params  # pyright: ignore[reportAssignmentType]
        if isinstance(params, list):
            await cur.executemany(query, parsed_params)
            return
        await cur.execute(query, parsed_params)
    except psycopg.OperationalError as error:
        if is_retry:
            raise error
        await pool.check()
        await exec_query(pool, cur, query, params, True)


def expand_values(
    table_name: LiteralString,
    values: PydanticParams,
    returning: Optional[list[LiteralString]] = None,
    **kwargs: Any,
) -> tuple[Composed, tuple[Any, ...]]:
    query = sql.SQL("INSERT INTO ") + sql.Identifier(table_name)
    if isinstance(values, BaseModel):
        raw = values.model_dump(**kwargs, exclude_none=True)
        vals = tuple(Jsonb(v) if _is_json(v) else v for v in raw.values())
        statement = (
            query
            + sql.SQL("(")
            + sql.SQL(", ").join(sql.Identifier(k) for k in raw.keys())
            + sql.SQL(")")
            + sql.SQL("VALUES")
            + sql.SQL("(")
            + sql.SQL(", ").join(sql.Placeholder() for _ in range(len(vals)))
            + sql.SQL(")")
        )
        statement = _returning(statement, returning)
        # debug = statement.as_string()
        return statement, vals

    models: list[dict[str, Any]] = []
    col_names: set[str] = set()
    row_sqls: list[sql.Composable] = []
    row_values: list[Any] = []
    for v in values:
        m_dict = v.model_dump(**kwargs, exclude_none=True)
        models.append(m_dict)
        col_names.update(m_dict.keys())

    for model in models:
        placeholders, row = list[sql.Composable](), list[Any]()
        for c in col_names:
            if c in model:
                placeholders.append(sql.Placeholder())
                row_val = model[c]
                row.append(Jsonb(row_val) if _is_json(row_val) else row_val)
            else:
                placeholders.append(sql.DEFAULT)
        row_sqls.append(sql.SQL("(") + sql.SQL(", ").join(placeholders) + sql.SQL(")"))
        row_values.extend(row)
    columns_sql = (
        sql.SQL("(") + sql.SQL(", ").join(sql.Identifier(col) for col in col_names) + sql.SQL(")")
    )
    statement = _returning(
        query + columns_sql + sql.SQL("VALUES") + sql.SQL(", ").join(row_sqls), returning
    )
    # debug = statement.as_string()
    return statement, tuple(row_values)


def _returning(statement: Composed, returning: Optional[list[LiteralString]] = None) -> Composed:
    return (
        statement
        + sql.SQL("RETURNING ")
        + sql.SQL(", ").join(sql.Identifier(col) for col in returning)
        if returning
        else statement
    )


def _is_json(value: object) -> bool:
    return isinstance(value, dict) or (isinstance(value, list) and isinstance(value[0], dict))


def _model_to_values(model: BaseModel, **kwargs: Any) -> tuple[Any, ...]:
    return tuple(
        Jsonb(v) if _is_json(v) else v
        for v in model.model_dump(**kwargs, exclude_none=True).values()
    )
