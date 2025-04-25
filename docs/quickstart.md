## Setup

To run the Quickstart examples, you will need the following Table:

```postgresql
CREATE TABLE comments
(
    id         SMALLSERIAL PRIMARY KEY,
    content    TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

some values to get started:

```postgresql
INSERT INTO comments (content)
VALUES ('This is a comment'),
       ('This is another comment');
```

and the following Python setup code:

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from python_postgres import Postgres


class Comment(BaseModel):
    content: str
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)


# TODO: Set your actual credentials
pg = Postgres("postgres", "password", "localhost")
```

## Basic Usage

You can use the `Postgres` instance to run queries the same way you would with a `psycopg` cursor,
and it will return results exactly the same way.
However, you do not need to create a connection or a cursor yourself. Instantiating `Postgres` creates a
Connection Pool and calling it will acquire a Connection from the Pool, spawn a Cursor on it, and execute your query.
After the query, the connection is returned to the Pool. Some examples:

```python
await pg(
    "INSERT INTO comments (content) VALUES (%s);", ("Hello from Python!",)
)  # You can pass a list of tuples to insert multiple rows at once
raw = await pg("SELECT * FROM comments;")
print(raw)
```

??? info "See Output"
    ```python
    [
        (
            1,
            "This is a comment",
            datetime.datetime(2025, 4, 24, 11, 53, 26, 419007),
            datetime.datetime(2025, 4, 24, 11, 53, 26, 419007),
        ),
        (
            2,
            "This is another comment",
            datetime.datetime(2025, 4, 24, 11, 53, 26, 419007),
            datetime.datetime(2025, 4, 24, 11, 53, 26, 419007),
        ),
        (
            3,
            "Hello from Python!",
            datetime.datetime(2025, 4, 24, 12, 56, 2, 939546),
            datetime.datetime(2025, 4, 24, 12, 56, 2, 939546),
        ),
    ]
    ```

??? example "Equivalent in `psycopg`"
    The above code condenses the following `psycopg` code for you (omitting error handling and handling of other cases):

    ```python
    con_str = f"postgresql://{user}:{quote_plus(password)}@{host}:{port}/{database}"
    con_pool = AsyncConnectionPool(con_str, min_size=10, max_size=50, open=False)
    
    await con_pool.open()
    async with con_pool.connection() as conn:
        async with conn.cursor(binary=True) as cur:
            await cur.execute("INSERT INTO comments (content) VALUES (%s);", ("Hello from Python!",))
            await conn.commit()
            num_inserted = cur.rowcount
        
        async with conn.cursor(binary=True) as cur:
            await cur.execute("SELECT * FROM comments;")
            raw = await cur.fetchall()
    ```

## Pydantic Models

Alternatively, you can pass Pydantic models as query parameters, and you can get results as models:

```python
await pg(
    "INSERT INTO comments (content, created_at, updated_at) VALUES (%s,%s,%s)",
    Comment(
        content="I was a pydantic model.",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    ),
)
# The inferred type of comments will be List[Comment]
comments = await pg("SELECT * FROM comments;", model=Comment)
print(res)
```

??? info "See Output"
    Note that this does not impact your query. The `SELECT *` query will still return all columns and send them over
    network, they will just not be included in the result set.
    ```python
    [
        Comment(
            content="This is a comment",
            created_at=datetime.datetime(2025, 4, 24, 11, 53, 26, 419007),
            updated_at=datetime.datetime(2025, 4, 24, 11, 53, 26, 419007),
        ),
        ...,
        Comment(
            content="I was a pydantic model.",
            created_at=datetime.datetime(2025, 4, 24, 16, 15, 51, 992358),
            updated_at=datetime.datetime(2025, 4, 24, 16, 15, 51, 992374),
        ),
    ]
    ```

### Dynamic Pydantic Inserts

You can pass a list of Pydantic models to the above query to insert multiple rows at once:

```python
comments = [
    Comment(
        content="This has both created_at and updated_at info.",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    ),
    Comment(content="This has created_at info.", created_at=datetime.now()),
    Comment(content="This has only content."),
]
await pg(
    "INSERT INTO comments (content, created_at, updated_at) VALUES (%s,%s,%s);",
    comments,
)
```

This will run just fine, but has a caveat: the `created_at` and `updated_at` fields are nullable in the database and
optional in the model. This leads to None values explicitly being passed to the database, derailing the default values
and producing these rows:

| id | content                                       | created_at                 | updated_at                 |
|----|-----------------------------------------------|----------------------------|----------------------------|
| 5  | This has both created_at and updated_at info. | 2025-04-24 16:43:23.383199 | 2025-04-24 16:43:23.383217 |
| 6  | This has created_at info.                     | 2025-04-24 16:43:23.383244 | null                       |
| 7  | This has only content.                        | null                       | null                       |

This is most likely not the intended behaviour. To address this, you can use the `insert()` method, which correctly 
expands the insert columns based on all non-`None` fields for each model and avoids passing None values to the database.
This still only produces one single query, inserting `DEFAULT` values where appropriate.

```python
await pg.insert("comments", comments)
```

!!! tip "You may not need this"
    Note that this specifically addresses the insertion of non-uniform models. If you are inserting a list of
    models that all have the same fields, you can still use the regular `INSERT INTO` syntax and pass the models
    as parameters directly, which is more efficient and allows for more elaborate Insert queries.

This will produce the following rows:

| id | content                                       | created_at                 | updated_at                 |
|----|-----------------------------------------------|----------------------------|----------------------------|
| 8  | This has both created_at and updated_at info. | 2025-04-24 17:06:32.316644 | 2025-04-24 17:06:32.316663 |
| 9  | This has created_at info.                     | 2025-04-24 17:06:32.316690 | 2025-04-24 15:06:31.499539 |
| 10 | This has only content.                        | 2025-04-24 15:06:31.499539 | 2025-04-24 15:06:31.499539 |

With this, the fields that were `null` before correctly get populated with the default values from the database, as is evident by the fact that all 3 of them hold identical values.

