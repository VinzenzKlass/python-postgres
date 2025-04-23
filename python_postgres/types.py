from typing import LiteralString

from psycopg.sql import SQL, Composed
from pydantic import BaseModel

type Query = LiteralString | SQL | Composed
type Params = tuple | list[tuple] | BaseModel | list[BaseModel] | Values


class Values:
    values: list[BaseModel] | BaseModel

    def __init__(self, values: BaseModel | list[BaseModel]):
        self.values = values
