<p align="center" style="margin: 0 0 10px">
<img width="200" height="200" src="https://www.postgresql.org/media/img/about/press/elephant.png" alt='Python' style="border-radius: 15px">
</p>

<h1 align="center" style="font-size: 3rem; font-weight: 400; margin: -15px 0">
Python Postgres
</h1>

---

pypostgres is an abstraction over [psycopg](https://www.psycopg.org/psycopg3/docs/index.html) and aims to provide the
simplest way to interact with PostgreSQL databases.

**I have just started this project, and it is not ready for production use. I am still working on every aspect of it.**

---

### Install postgresql

```shell
pip install postgresql
```

### Usage

```python
from python_postgres import Postgres

pg = Postgres("pgadmin", "password", "pg-is-king.postgres.database.azure.com")


async def main():
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
```





