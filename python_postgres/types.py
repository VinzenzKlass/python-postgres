from typing import LiteralString

from psycopg.sql import SQL, Composed
from pydantic import BaseModel

type Query = LiteralString | SQL | Composed
type PydanticParams = BaseModel | list[BaseModel]
type Params = tuple | list[tuple] | PydanticParams
