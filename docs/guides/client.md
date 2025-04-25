One of the main benefits of Python Postgres is the ability to run arbitrary SQL queries and having a simple pydantic model
to represent the results. This is particularly handy when you do not want to maintain pydantic models for every table
in your database, when you're just not interested in most of them but instead only in certain compositions of them.

??? example "Setup"
    ```postgresql 
    CREATE TABLE customers (
      customer_id SERIAL PRIMARY KEY,
      first_name VARCHAR(50) NOT NULL,
      last_name VARCHAR(50) NOT NULL,
      email VARCHAR(100) UNIQUE NOT NULL,
      phone VARCHAR(20),
      birth_date DATE,
      address JSONB,
      loyalty_points INTEGER DEFAULT 0,
      segment VARCHAR(20) CHECK (segment IN ('STANDARD', 'PREMIUM', 'VIP')),
      preferences TEXT[],
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
      last_login TIMESTAMP WITH TIME ZONE,
      is_active BOOLEAN DEFAULT TRUE
    );

    CREATE TABLE products (
      product_id SERIAL PRIMARY KEY,
      sku VARCHAR(20) UNIQUE NOT NULL,
      name VARCHAR(100) NOT NULL,
      description TEXT,
      price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
      cost DECIMAL(10, 2) CHECK (cost >= 0),
      category VARCHAR(50) NOT NULL,
      subcategory VARCHAR(50),
      attributes JSONB,
      stock_quantity INTEGER NOT NULL DEFAULT 0,
      reorder_level INTEGER,
      weight DECIMAL(8, 2),
      dimensions VARCHAR(50),
      is_discontinued BOOLEAN DEFAULT FALSE,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE orders (
      order_id SERIAL PRIMARY KEY,
      customer_id INTEGER REFERENCES customers (customer_id),
      order_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
      status VARCHAR(20) CHECK (
        status IN (
          'PENDING',
          'PROCESSING',
          'SHIPPED',
          'DELIVERED',
          'CANCELLED'
        )
      ),
      total_amount DECIMAL(12, 2) NOT NULL,
      discount_amount DECIMAL(12, 2) DEFAULT 0,
      tax_amount DECIMAL(12, 2) DEFAULT 0,
      shipping_address JSONB,
      payment_method VARCHAR(50),
      tracking_number VARCHAR(100),
      notes TEXT,
      items JSONB NOT NULL,
      shipping_date TIMESTAMP WITH TIME ZONE,
      delivery_date TIMESTAMP WITH TIME ZONE
    );
    ```

In real-world examples, you may often find queries like this:

??? example "Query"
    ```postgresql
    SELECT
        c.customer_id,
        c.first_name || ' ' || c.last_name AS customer_name,
        c.segment AS customer_segment,
        o.order_date,
        p.name AS top_product_name,
        p.category,
        SUM(o.total_amount) OVER (
            PARTITION BY
                c.customer_id
            ) AS customer_lifetime_value,
        RANK() OVER (
            PARTITION BY
                p.category
            ORDER BY
                o.total_amount DESC
            ) AS category_rank
    FROM
        customers c
            INNER JOIN orders o ON c.customer_id = o.customer_id
            INNER JOIN LATERAL (
            SELECT
                p.product_id,
                p.name,
                p.category,
                p.price
            FROM
                products p
            WHERE
                p.product_id = ANY (
                       SELECT
                           (jsonb_array_elements(o.items) ->> 'product_id')::INTEGER
                       )
            ORDER BY
                p.price DESC
            LIMIT
                1
            ) p ON TRUE
    WHERE
        c.is_active = TRUE
      AND o.status IN ('SHIPPED', 'DELIVERED')
      AND o.order_date >= CURRENT_DATE - INTERVAL '1 year'
    GROUP BY
        c.customer_id,
        c.first_name,
        c.last_name,
        c.segment,
        o.order_date,
        p.name,
        p.category,
        o.total_amount
    HAVING
        SUM(o.total_amount) > 1000
    ORDER BY
        customer_lifetime_value DESC,
        order_date DESC
    LIMIT
        100;
    ```

For some example values, this would yield:

| customer_id | customer_name | customer_segment | order_date                        | top_product_name | category    | customer_lifetime_value | category_rank |
|:------------|:--------------|:-----------------|:----------------------------------|:-----------------|:------------|:------------------------|:--------------|
| 2           | Maria Garcia  | VIP              | 2025-04-25 09:31:34.621258 +00:00 | Premium Laptop   | Electronics | 1479.98                 | 1             |
| 1           | John Smith    | PREMIUM          | 2025-04-25 09:31:34.621258 +00:00 | Premium Laptop   | Electronics | 1349.99                 | 2             |

In this scenario, not only would it be quite cumbersome to maintain models for all the tables with appropriate types 
and constraints, but rewriting this query in an ORM syntax would probably be somewhat tedious, if we're only 
interested in the result of this query and not in the tables themselves.

??? tip "Actually ..."
    You could of course use a view for the above, but that can both be unwanted for a whole number of reasons, and is
    besides the point of this illustrative example.

With Python Postgres, you can simply run this query and get a pydantic model with the result:


```python
class CustomerOrderAnalytics(BaseModel):
    customer_id: int
    customer_name: str
    customer_segment: Literal["STANDARD", "PREMIUM", "VIP"]
    order_date: datetime
    top_product_name: str
    category: str
    customer_lifetime_value: Decimal
    category_rank: int

data = await pg(query, model=CustomerOrderAnalytics)
print(data)
```

```python
[
    CustomerOrderAnalytics(
        customer_id=2,
        customer_name="Maria Garcia",
        customer_segment="VIP",
        order_date=datetime.datetime(
            2025, 4, 25, 9, 31, 34, 621258, tzinfo=datetime.timezone.utc
        ),
        top_product_name="Premium Laptop",
        category="Electronics",
        customer_lifetime_value=Decimal("1479.98"),
        category_rank=1,
    ),
    CustomerOrderAnalytics(
        customer_id=1,
        customer_name="John Smith",
        customer_segment="PREMIUM",
        order_date=datetime.datetime(
            2025, 4, 25, 9, 31, 34, 621258, tzinfo=datetime.timezone.utc
        ),
        top_product_name="Premium Laptop",
        category="Electronics",
        customer_lifetime_value=Decimal("1349.99"),
        category_rank=2,
    ),
]
```
