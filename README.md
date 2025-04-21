<p align="center" style="margin: 0 0 10px">
<img width="200" height="200" src="https://www.postgresql.org/media/img/about/press/elephant.png" alt='Python' style="border-radius: 15px">
</p>

<h1 align="center" style="font-size: 3rem; font-weight: 400; margin: -15px 0">
Python Postgres
</h1>

---

Python Postgres is an abstraction over [psycopg](https://www.psycopg.org/psycopg3/docs/index.html) and aims to provide
a simple, SQL-based way to interact with PostgreSQL databases in Python. Ultimately, this project is an
in-between between an ORM and a database driver. Everything is done through SQL and there are no ORM-specific
expressions to learn. You always have the full flexibility and control of SQL, but you also get some of the benefits
that ORMs typically provide, like parsing of results to Pydantic models and the autocomplete, linting etc. that
comes alongside that. Further, it reduces the amount of boilerplate code you have to write when using psycopg directly,
while still exposing all its features to you, where you need them.

**I have just started this project, and it is not ready for production use. I am still working on every aspect of it and
it is entirely experimental. I may abandon this project at any point without warning.**

---

### Installation

```shell
pip install python_postgres 
```

### Basic Usage

Given this table:

```sql
CREATE TABLE IF NOT EXISTS public.sales
(
    invoice_id    CHAR(11),
    branch        CHAR,
    city          TEXT,
    customer_type CHAR(6),
    gender        BOOLEAN,
    product_line  TEXT,
    unit_price    DOUBLE PRECISION,
    quantity      INTEGER,
    tax           DOUBLE PRECISION,
    total         DOUBLE PRECISION,
    date          DATE,
    time          CHAR(5),
    payment       TEXT,
    cogs          DOUBLE PRECISION,
    gross_margin  DOUBLE PRECISION,
    gross_income  DOUBLE PRECISION,
    rating        DOUBLE PRECISION
);
```

you can run the below example. Instantiating the `Postgres` class will create a connection pool with the given
credentials. Calling this class will grab a connection from the pool (potentially waiting until one is available), spawn
a binary Cursor on it and execute the query, automatically commiting where necessary. After the query is executed, it
will return the connection to the pool and return the result, if available, or the number of affected rows. It also will
evict stale or inactive connections from the pool when one is encountered.

```python
from python_postgres import Postgres

pg = Postgres("pgadmin", "password", "localhost")  # TODO: Set your actual credentials

sales = await pg("SELECT * FROM sales LIMIT 10;")
print(sales)
```

```python
[
    Result(
        invoice_id="750-67-8428",
        branch="A",
        city="Yangon",
        customer_type="Member",
        gender=False,
        product_line="Health and beauty",
        unit_price=74.69,
        quantity=7,
        tax=26.1415,
        total=548.9715,
        date=datetime.date(2019, 1, 5),
        time="13:08",
        payment="Ewallet",
        cogs=522.83,
        gross_margin=4.761904762,
        gross_income=26.1415,
        rating=9.1,
    ),
    ...,
    Result(
        invoice_id="226-31-3081",
        branch="C",
        city="Naypyitaw",
        customer_type="Normal",
        gender=False,
        product_line="Electronic accessories",
        unit_price=15.28,
        quantity=5,
        tax=3.82,
        total=80.22,
        date=datetime.date(2019, 3, 8),
        time="10:29",
        payment="Cash",
        cogs=76.4,
        gross_margin=4.761904762,
        gross_income=3.82,
        rating=9.6,
    ),
]
```

If you do not specify a model, the result will be a list of `Result` objects. `Result` is a pydantic model generated
from all columns in the query. You can specify a model like this:

```python
from pydantic import BaseModel


class Sales(BaseModel):
    invoice_id: str
    city: str
    quantity: int
    total: float


sales = await pg("SELECT * FROM sales LIMIT 10;", model=Sales)
print(sales)
```

```python
[
    Sales(invoice_id="750-67-8428", city="Yangon", quantity=7, total=548.9715),
    Sales(invoice_id="226-31-3081", city="Naypyitaw", quantity=5, total=80.22),
    Sales(invoice_id="750-67-8428", city="Yangon", quantity=7, total=548.9715),
    Sales(invoice_id="226-31-3081", city="Naypyitaw", quantity=5, total=80.22),
    Sales(invoice_id="631-41-3108", city="Yangon", quantity=7, total=340.5255),
    Sales(invoice_id="123-19-1176", city="Yangon", quantity=8, total=489.048),
    Sales(invoice_id="373-73-7910", city="Yangon", quantity=7, total=634.3785),
    Sales(invoice_id="699-14-3026", city="Naypyitaw", quantity=7, total=627.6165),
    Sales(invoice_id="750-67-8428", city="Yangon", quantity=7, total=548.9715),
    Sales(invoice_id="226-31-3081", city="Naypyitaw", quantity=5, total=80.22),
]
```

You can opt out of this altogether by instantiating the `Postgres` class with `return_raw=True`. This will return the
raw results as provided by psycopg.

### Inserting Data

You can pass Pydantic models to the `Values` class, which will automatically expand the insert statement for you.
The insert columns will be inferred from the model field names. This also correctly populates the query if a list of
non-uniform models is passed, saving you from having to manually specify the columns in several insert statements. You
can pass both a single model or a list of models to the `Values` class. Either one will parametrize one single query and
send it to the database alongside the values.

Given the following table:

```sql
CREATE TABLE public.comments
(
    id         SMALLSERIAL PRIMARY KEY,
    content    TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

You can run the following code:

```python
import datetime
from python_postgres import Values
from typing import Optional
from pydantic import BaseModel, Field


class Comment(BaseModel):
    content: str
    created_at: Optional[datetime.datetime] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


async def main():
    comments = [
        Comment(
            content="This has both created_at and updated_at info.",
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
        ),
        Comment(content="This has created_at info.", created_at=datetime.datetime.now()),
        Comment(content="This has only content."),
    ]
    await pg("INSERT INTO comments ", Values(comments))
    await pg("INSERT INTO comments ", Values(Comment(content="This comment is a solo.")))
```

The result will be:

| id | content                                       | created_at                 | updated_at                 |
|----|-----------------------------------------------|----------------------------|----------------------------|
| 1  | This has both created_at and updated_at info. | 2025-04-21 19:12:51.080427 | 2025-04-21 19:12:51.080443 |
| 2  | This has created_at info.                     | 2025-04-21 19:12:51.080459 | 2025-04-21 17:12:51.528062 |
| 3  | This has only content.                        | 2025-04-21 17:12:51.528062 | 2025-04-21 17:12:51.528062 |
| 4  | This comment is a solo.                       | 2025-04-21 17:12:51.545619 | 2025-04-21 17:12:51.545619 |

Looking at the table, you can see that the first row has different values for `created_at` and `updated_at`, because
they were sequentially generated in python. The second row has different values for `created_at` and `updated_at`,
because the updated_at value was generated in the database. The third row has the same value for `created_at` and
`updated_at`, because they were both generated in the database. The values are also the same as the one for the
`created_at` column of the second row, because they were generated in the same transaction. The fourth row has the same
value for `created_at` and `updated_at`, because they were both generated in the database, but different ones than the
ones from the previous transaction.

You don't have to use Pydantic models, you can also psycopg-like statements like this:

```python
await pg("INSERT INTO comments (content) VALUES (%s);", [("Comment 1",), ("Comment 2",)])
```

In these cases you must construct the entire query yourself.

### Notes

Other than providing simpler syntax through a thin abstraction, this project inherits all the design choices of psycopg,
including the [caching of query execution plans](https://www.psycopg.org/psycopg3/docs/advanced/prepare.html#index-0)
