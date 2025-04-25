This Project requires `Python>=3.12`.

### Install

By default, python-postgres will install the pure python version of psycopg and the pool extra. Just like psycopg
itself, you can install it with the `binary` or `c` extras. Whenever possible, you should prefer the `c` version,
especially for production use cases. Read more about the distribution options in
the [psycopg documentation](https://www.psycopg.org/psycopg3/docs/basic/install.html).

=== "pip"
    ```shell
    pip install python-postgres[c]
    ```

=== "uv"
    ```shell
    uv add python-postgres[c]
    ```

=== "Poetry"
    ```shell
    poetry add python-postgres[c]
    ```

If this fails, you can try the `binary` or pure-python version.

=== "pip"
    ```shell
    pip install python-postgres[binary]
    ```

    ```shell
    pip install python-postgres
    ```

=== "uv"
    ```shell
    uv add python-postgres[binary]
    ```

    ```shell
    uv add python-postgres
    ```

=== "Poetry"
    ```shell
    poetry add python-postgres[binary]
    ```

    ```shell
    poetry add python-postgres
    ```
