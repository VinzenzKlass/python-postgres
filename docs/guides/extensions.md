You can use extensions that require extending the driver by for e.g. adding additional types. If the extension you're
interested in provides such an extension compatible with psycopg `AsyncConnection`, you can use it as you would with
psycopg directly. You can pass these extensions to the `patch` parameter when instantiating your instance of
`Postgres`.

```python
pg = Postgres(
    "postgres", "password", "localhost", patch=[register_my_extension]
)
```

## Example: [pgvector](https://github.com/pgvector/pgvector)


```python
import numpy as np
from pydantic import BaseModel, ConfigDict
from pgvector.psycopg import register_vector_async


class Item(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: int
    embedding: np.ndarray

pg = Postgres(
    "postgres", "password", "localhost", patch=[register_vector_async]
)

async def main():
    await pg(
        "CREATE TABLE items (id bigserial PRIMARY KEY, embedding vector(3));"
    )
    embedding = np.array([1, 2, 3])
    await pg("INSERT INTO items (embedding) VALUES (%s)", (embedding,))
    res = await pg(
        "SELECT * FROM items ORDER BY embedding <=> %s;",
        (embedding,),
        model=Item,
    )
    print(res)
```
```python
[Item(id=1, embedding=array([1., 2., 3.], dtype=float32))]
```

