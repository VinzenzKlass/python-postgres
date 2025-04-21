from typing import LiteralString

from psycopg.sql import SQL, Composed
from pydantic import BaseModel

from ._adapters import Values

type Query = LiteralString | SQL | Composed
type Params = tuple | list[tuple] | BaseModel | list[BaseModel] | Values
