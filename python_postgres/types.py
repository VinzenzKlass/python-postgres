from typing import Any, Callable, Coroutine, Iterable, LiteralString

from psycopg import AsyncConnection
from psycopg.sql import SQL, Composed
from pydantic import BaseModel

type Query = LiteralString | SQL | Composed
type PydanticParams = BaseModel | list[BaseModel]
type Params = tuple | list[tuple] | PydanticParams
type AsyncConnectionPatch = Iterable[Callable[[AsyncConnection], Coroutine[Any, Any, None]]]
