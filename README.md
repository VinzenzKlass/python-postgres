<p align="center" style="margin: 0 0 10px">
<img width="200" height="200" src="https://www.postgresql.org/media/img/about/press/elephant.png" alt='Python' style="border-radius: 15px">
</p>

<h1 align="center" style="font-size: 3rem; font-weight: 400; margin: -15px 0">
Python Postgres
</h1>

---

Python Postgres is an abstraction over [psycopg](https://www.psycopg.org/psycopg3/docs/index.html) and aims to provide
the simplest way to interact with PostgreSQL databases in Python.

**I have just started this project, and it is not ready for production use. I am still working on every aspect of it and
may abandon it at any point without warning.**

---

### Installation

```shell
pip install python_postgres 
```

### Basic Usage

```python
from python_postgres import Postgres

pg = Postgres("pgadmin", "password", "pg-is-king.postgres.database.azure.com")


async def main():
    await pg.open()  # Open the connection pool, this requires a running event loop.
    files = await pg("SELECT * FROM files")
    await pg("INSERT INTO files (name, size) VALUES (%s, %s)", [("file1", 1024), ("file2", 2048)])

    async with pg.transaction() as tran:
        file_id = (
            await tran(
                "INSERT INTO files (name, size) VALUES VALUES (%s, %s) RETURNING file_id;",
                ("you_may_not_exist", 0),
            )
        )[0]
        await tran("INSERT INTO pages (page_number, file_id) VALUES (%s, %s);", (4, file_id))
        raise ValueError("Oopsie")
    await pg.close()  # Close the connection pool. Python Postgres will attempt to automatically
    # close the pool when the instance is garbage collected, but this is not guaranteed to succeed.
    # Be civilized and close it yourself.
```

### Pydantic Integration

Python Postgres supports [Pydantic](https://docs.pydantic.dev/latest/) Models as insert parameters.

```python
from pydantic import BaseModel


class File(BaseModel):
    file_name: str
    size: int


async def main():
    await pg.open()
    await pg(
        "INSERT INTO files (file_name, size) VALUES (%s, %s)",
        File(file_name="rubbish.pdf", size=8096),
    )
    await pg.close()
```

Since this can be cumbersome and redundant to spell out, Python Postgres can generate this Query for you.

```python
class File(BaseModel):
    file_name: str
    size: int
    internal_only_field: str = "This field must not be written to the database"
    field_1: Optional[str] = None
    field_2: Optional[str] = None
    field_3: Optional[str] = None
    field_4: Optional[str] = None
    field_5: Optional[str] = None
    field_6: Optional[str] = None
    field_7: Optional[str] = None
    field_8: Optional[str] = None
    field_9: Optional[str] = None
    field_10: Optional[str] = None


async def main():
    await pg.open()
    await pg.write_pydantic(
        "features", File(file_name="rubbish.pdf", size=8096), exclude={"internal_only_field"}
    )
    await pg.close()
``` 

This will generate the following query before calling it with the value of the passed model. You can also pass a list of
models to insert multiple rows at once. The extra keywords arguments will be passed to the model serialization.

```sql
INSERT INTO "features" ("file_name", "size", "field_1", "field_2", "field_3", "field_4", "field_5", "field_6",
                        "field_7", "field_8", "field_9", "field_10")
VALUES ($1, $2, $3, $4, $5 $6, $7, $8, $9, $10, $11, $12) 
```

**Python Postgres does not aim to be an ORM or provide an object-oriented experience, and it will not generate queries
for you beyond this one use-case.** If you are looking for a Pydantic based ORM, have a look
at [SQLModel](https://sqlmodel.tiangolo.com/).
Python Postgres is focused on SQL and in this case just provides this utility around Pydantic to support one further
Type you can pass as parameters to your queries.

### A more in-depth look

The basic idea of this project is to provide one callable instance of the `Postgres` class. The `Postgres` class manages
a connection pool in the background and will get a connection from the pool when called, spawn a binary cursor on it,
run your query, return the results (or the number of rows affected), and then return the connection to the pool. As a
query, you can pass either a literal - string or bytes - or a `SQL` or
`Composed` [object](https://www.psycopg.org/psycopg3/docs/api/sql.html) from the `psycopg` library.

In Essence, the `Postgres` class is syntactic sugar for turning this:

```python
async def exec_query(
        query: LiteralString | bytes | SQL | Composed,
        params: tuple | list[tuple],
        is_retry: bool = False,
) -> list[tuple]:
    try:
        async with con_pool.connection() as con:  # type: psycopg.AsyncConnection
            async with con.cursor(binary=True) as cur:  # type: psycopg.AsyncCursor
                if isinstance(params, list):
                    await cur.executemany(query, params)
                else:
                    await cur.execute(query, params)
                await con.commit()
                return (
                    await cur.fetchall()
                    if cur.pgresult and cur.pgresult.ntuples > 0
                    else cur.rowcount or -1
                )
    except psycopg.OperationalError as error:
        if is_retry:
            raise IOError from error
        await con_pool.check()
        await exec_query(query, params, True)
    except psycopg.Error as error:
        raise IOError from error


await exec_query("SELECT * FROM files WHERE id = %s", (1234,))
```

into

```python
await pg("SELECT * FROM files WHERE id = %s", (1234,))
```

### Notes

Other than providing simpler syntax through a thin abstraction, this project inherits all the design choices of psycopg,
including the [caching of query execution plans](https://www.psycopg.org/psycopg3/docs/advanced/prepare.html#index-0)
