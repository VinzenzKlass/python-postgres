from typing import LiteralString

from psycopg.sql import SQL, Composed

type Query = LiteralString | bytes | SQL | Composed
type Params = tuple | list[tuple]
