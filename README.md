# querky
Turn your SQL queries into type annotated Python functions and autogenerated types with a single decorator.

# Showcase

This example shows what `querky` SQL functions look like.

Consider this PostgreSQL database schema:

```sql
CREATE TABLE account (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT,
    phone_number TEXT,
    balance BIGINT NOT NULL DEFAULT 0,
    join_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    referred_by_account_id BIGINT REFERENCES account (id)
);

CREATE TABLE post (
    id BIGSERIAL PRIMARY KEY,
    poster_id BIGINT NOT NULL REFERENCES account (id),
    message TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE post_comment (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT NOT NULL REFERENCES post (id),
    commenter_id BIGINT NOT NULL REFERENCES account (id),
    message TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

And these are the queries defined on it:

```python
from querky_def import qrk


# an UPDATE query: no value returned
@qrk.query  # or @qrk.query(shape='status')
def update_account_phone_number(account_id, new_phone_number):
    return f'''
        UPDATE
            account
        SET
            phone_number = {+new_phone_number}
        WHERE
            id = {+account_id}
        '''


# an INSERT query to always return a single value
@qrk.query(shape='value', optional=False)
def insert_account(username, first_name, last_name, phone_number, balance, referred_by_account_id):
    return f'''
        INSERT INTO
            account
            (
                username,
                first_name,
                last_name,
                phone_number,
                balance,
                referred_by_account_id
            )
        VALUES
            (
                {+username},
                {+first_name},
                {+last_name},
                {+phone_number},
                {+balance},
                {+referred_by_account_id}
            )
        RETURNING
            id
        '''


# a SELECT query to return an array of single values
@qrk.query(shape='column')
def select_top_largest_balances(limit):
    return f'''
        SELECT
            balance
        FROM
            account
        ORDER BY
            balance DESC
        LIMIT
            {+limit}
        '''


# now for the most interesting part: fetching rows
# a SELECT query to return a single (one) AccountReferrer row or None (optional)
@qrk.query('AccountReferrer', shape='one', optional=True)
def get_account_referrer(account_id):
    return f'''
        SELECT
            referrer.id,
            referrer.username,
            referrer.first_name,
            referrer.last_name,
            referrer.join_ts

        FROM 
            account

        INNER JOIN
            account AS referrer
        ON
            account.referred_by_account_id = referrer.id

        WHERE
            account.id = {+account_id}
        '''


# a SELECT query to return many (an array of) AccountPostComment rows
@qrk.query('AccountPostComment', shape='many')
def select_last_post_comments(post_id, limit):
    return f'''
        SELECT 
            account.first_name,
            account.last_name,
            post_comment.id,
            post_comment.message

        FROM
            post_comment

        INNER JOIN
            account
        ON
            post_comment.commenter_id = account.id

        WHERE
            post_comment.post_id = {+post_id}

        ORDER BY
            post_comment.ts DESC

        LIMIT
            {+limit}
        '''

```

So, as you can see, all you need is **3 simple steps**: 

1. <u>**Write a Python function**</u> returning the desired SQL query.

2. <u>**Insert the arguments**</u> exactly where you want them to be. *Don't forget to prepend your arguments with a plus sign* (`+`). Even though it is a regular Python format string, **the resulting query is not SQL-injectable**, as you'll later see.

3. <u>**Add the `@qrk.query` decorator**</u> using arguments to describe the expected shape and type of result set.  

Before you can use this code, **you'll need the `qrk` object**. 

Bear with me, I'll show the full configuration in the next section, but, firstly, I would like to show *the results of running `querky`'s code generator*. Here it is:


```python
# ~ AUTOGENERATED BY QUERKY ~ #
import datetime
from asyncpg import Connection
from dataclasses import dataclass
from sql.example import update_account_phone_number as _q0
from sql.example import insert_account as _q1
from sql.example import select_top_largest_balances as _q2
from sql.example import get_account_referrer as _q3
from sql.example import select_last_post_comments as _q4


async def update_account_phone_number(__conn: Connection, /, account_id: int, new_phone_number: str) -> str:
    return await _q0.execute(__conn, account_id, new_phone_number)


async def insert_account(__conn: Connection, /, username: str, first_name: str, last_name: str, phone_number: str, balance: int, referred_by_account_id: int) -> int:
    return await _q1.execute(__conn, username, first_name, last_name, phone_number, balance, referred_by_account_id)


async def select_top_largest_balances(__conn: Connection, /, limit: int) -> list[int]:
    return await _q2.execute(__conn, limit)


@dataclass(slots=True)
class AccountReferrer:
    id: int
    username: str
    first_name: str
    last_name: str
    join_ts: datetime.datetime


async def get_account_referrer(__conn: Connection, /, account_id: int) -> AccountReferrer | None:
    return await _q3.execute(__conn, account_id)

_q3.bind_type(AccountReferrer)


@dataclass(slots=True)
class AccountPostComment:
    first_name: str
    last_name: str
    id: int
    message: str


async def select_last_post_comments(__conn: Connection, /, post_id: int, limit: int) -> list[AccountPostComment]:
    return await _q4.execute(__conn, post_id, limit)

_q4.bind_type(AccountPostComment)


__all__ = [
    "select_last_post_comments",
    "AccountPostComment",
    "AccountReferrer",
    "insert_account",
    "update_account_phone_number",
    "get_account_referrer",
    "select_top_largest_balances",
]
```

So, let's analyze what we got:

- **We have all of our input and output types defined**. The linter can now help us whenever we use any of these functions and types in our code.
- **Whenever the database schema changes, the types and function arguments will accommodate automatically**: just run the generation script again - and you're set.
- **All the types were inferred from a live database connection**, because <u>your database is the single source of truth for your data</u>, not the application.
- **Our "models" are database rows**. At last.

*Do not be discouraged, if you don't like using dataclasses in your projects*, as this is just an example!

So, if you like what you're seeing, let's configure your project!

# Basic Configuration

## [asyncpg](https://github.com/MagicStack/asyncpg)

To install, run
```
pip install querky[asyncpg]
```


Consider this project structure:

```
src
|__ querky_def.py
|__ querky_gen.py
|__ sql
    |__ example.py
```

`sql` folder contains `.py` files with the query functions. Generated code will be placed in the `sql/queries` folder under the same name as the inital script (`example.py` in this case).

`querky_gen.py` file is the code generation script. You run it when you want to regenerate the query functions:

```python
import asyncio

from querky.presets.asyncpg import generate

from querky_def import qrk
import sql
from env import CONNECTION_STRING


if __name__ == "__main__":
    asyncio.run(generate(qrk, CONNECTION_STRING, base_modules=(sql, )))

```

`querky_def.py` is code generator configuration. We'll use a preset for the sake of simplicity.

```python
import os
from querky.presets.asyncpg import use_preset


qrk = use_preset(os.path.dirname(__file__), type_factory='dataclass+slots')
```

> The first argument should be the path to the root directory of your project.

> If you'd like more fine-grained control over the `Querky` object, there will be an explaination in the later sections.

After the configuration of the `qrk` object it's time to run the `querky_gen.py` script. 

Each of your queries will become type hinted, each of them will return a real Python object, 
and you can call these queries as regular Python functions.

Every time you change your database schema or queries, you can now expect the changes to propagate throughout your code. 
Because of that, **refactoring SQL-dependent code has never been easier**. *This time the linter is on your side.*

> Do not change the generated files, as they are transient and will be overwritten. 
> If you need to modify the generated code, consider using `on_before_func_code_emit` and `on_before_type_code_emit` hooks passed in to the `Querky` object constructor.

# Type Hinting Extensions

## Arguments
### Optionals

A careful reader might have noticed, that the generated argument types are never optional.
If we go back to the database schema, we will notice, that some of the columns are `NULLABLE`. 
And yet, in `insert_account` query the respective arguments are not `Optional`. 

Why is that?

Unfortunately, there is no *straightforward* way for the library to automate this process, 
because SQL-wise these are constraints, and not data types.

So, it's our job to hint the library to do the right thing.

Let's look at the signature of this function again:

```python
@qrk.query(shape='value', optional=False)
def insert_account(
        username, 
        first_name, 
        last_name, 
        phone_number, 
        balance, 
        referred_by_account_id
):
    ...
```

We know that `phone_number`, `last_name` and `referred_by_account_id` are optional. So we just hint them like this:

```python
import typing

@qrk.query(shape='value', optional=False)
def insert_account(
        username, 
        first_name, 
        last_name: typing.Optional, 
        phone_number: typing.Optional, 
        balance, 
        referred_by_account_id: typing.Optional
):
    ...
```

Then, the generated function's signature will look like this:

```python
async def insert_account(
        __conn: Connection, 
        /, 
        username: str, 
        first_name: str, 
        last_name: str | None, 
        phone_number: str | None, 
        balance: int, 
        referred_by_account_id: int | None
) -> int:
    ...
```

### Default values

Let's consider the same `insert_account` query.

Let's make `referred_by_account_id` `None` by default:

```python
@qrk.query(shape='value', optional=False)
def insert_account(
        username, 
        first_name, 
        last_name: typing.Optional, 
        phone_number: typing.Optional, 
        balance, 
        referred_by_account_id=None
):
    ...
```

We'll get this signature:

```python
async def insert_account(
        __conn: Connection, 
        /, 
        username: str, 
        first_name: str, 
        last_name: str | None, 
        phone_number: str | None, 
        balance: int, 
        referred_by_account_id: int | None = _q1.default.referred_by_account_id
) -> int:
    ...
```

`_q1` is a reference to the original `insert_account` `Query` object, which contains the default value for this argument.

This way any kind of default argument can be used, 
since the generated function always references the original value.


> Notice that we got rid of `typing.Optional` from `referred_by_account_id`'s annotation, 
> yet the generated signature is still `int | None`. 
> This "type-inference" behavior holds only for the `None` default value.

### Enforce type

Sometimes even type inference from the database itself does not help. 
A prime example would be the infamous `postgres`' `ARRAY[]` type.
Values of this type can have an arbitrary number of dimensions. 

[Postgres docs](https://www.postgresql.org/docs/current/arrays.html):
> The current implementation does not enforce the declared number of dimensions either. Arrays of a particular element type are all considered to be of the same type, regardless of size or number of dimensions. So, declaring the array size or number of dimensions in CREATE TABLE is simply documentation; it does not affect run-time behavior.

But oftentimes we find ourselves with a well-known structure, 
even though the type itself is permissive (*hello, Python!*).

Consider this query:

```python
@qrk.query(shape='value', optional=False)
def are_2d_matrices_equal(m):
    return f"SELECT {+m} = ARRAY[[1,2,3], [1,2,3], [1,2,3]]::INTEGER[]"
```

It yields this signature:

```python
async def are_2d_matrices_equal(__conn: Connection, /, m: list[int]) -> bool:
    ...
```

Now, let's enforce our knowledge, that this array is two-dimensional.

The way we do it is by regular PEP484 annotations:

```python
@qrk.query(shape='value', optional=False)
def are_2d_matrices_equal2(m: 'list[list[int]]'):
    return f"SELECT {+m} = ARRAY[[1,2,3], [1,2,3], [1,2,3]]::INTEGER[]"
```

And get this in return:

```python
async def are_2d_matrices_equal2(__conn: Connection, /, m: list[list[int]]) -> bool:
    ...
```

> **Overriding annotations must always be strings.**
This is because they are literally copied from the source file into the generated one by using function annotation introspection. 
If they were objects, this wouldn't be reliable.

## Return types

The same problems apply to fields of a row. 

They, same as arguments, can be optional, can have a different type from the inferred one.

For example, let's pimp the `get_account_referrer` query, since `last_name` is nullable.

To do that, we need to import the `attr` object:

```python
from querky import attr

@qrk.query('AccountReferrer', shape='one', optional=True)
def get_account_referrer(account_id):
    return f'''
        SELECT
            referrer.id,
            referrer.username,
            referrer.first_name,
            referrer.last_name AS {attr.last_name(optional=True)},
            referrer.join_ts

        FROM 
            account

        INNER JOIN
            account AS referrer
        ON
            account.referred_by_account_id = referrer.id

        WHERE
            account.id = {+account_id}
        '''
```

The generated type will now look like this:

```python
@dataclass(slots=True)
class AccountReferrer:
    id: int
    username: str
    first_name: str
    last_name: str | None
    join_ts: datetime.datetime
```

Notice, how `last_name` is now optional. 

You can also use `-attr.last_name` syntax for optional fields.

To override the generated annotation use this syntax:

```python
@qrk.query(shape='one')
def get_row():
    return f'''
        SELECT
            ARRAY[[1,2,3], [1,2,3], [1,2,3]]::INTEGER[] AS {attr.matrix2d('list[list[int]]')},
            ARRAY[[[1,2,3],[1,2,3]], [[1,2,3],[1,2,3]], [[1,2,3],[1,2,3]]]::INTEGER[] AS {attr.matrix3d('list[list[list[int]]]')},
            'Looks like text' AS {attr.definitely_not_text('float')}
        '''
```

Generates this:

```python
@dataclass(slots=True)
class SimpleRow:
    matrix2d: list[list[int]]
    matrix3d: list[list[list[int]]]
    definitely_not_text: float
```


> This looks a bit like magic, but here is how it works: 
> `attr` object is a singleton, which records each `__getattr__` invocation, returning an `Attr` object in its stead.
> When the `Attr` object is called, it records the arguments, and returns a string with which the `__getattr__` was invoked.
> Once the code inside `@qrk.query` decorated function is run,
> it flushes all the recorded `Attr` objects into the query. Then, when the code is being generated,
> those objects serve to complete the type information about their respective fields.

### Different queries - same return type

Sometimes there is a couple of different ways to get to the same data.

Consider these queries:

```python
@qrk.query('AccountInfo', shape='one')
def get_account(account_id):
    return f'''
        SELECT 
            first_name,
            last_name,
            username,
            phone_number
        FROM
            account
        WHERE
            id = {+account_id}
        '''


@qrk.query('???', shape='one')
def get_last_joined_account():
    return f'''
        SELECT 
            first_name,
            last_name,
            username,
            phone_number
        FROM
            account
        ORDER BY
            join_ts DESC
        LIMIT
            1
        '''
```

What do we call the second type to not clash with the first one? 
`AccountInfo2`? 

It can be done this way, however this would potentially
lead to many weirdly named duplicate types across the project.

Instead, just pass in the `get_account` query in place of the first parameter:

```python
@qrk.query(get_account, shape='one')
def get_last_joined_account():
    ...
```

This way the type won't be generated the second time, 
and the code will use the "parent type" in runtime.

> You can use queries from other modules, too. Just import them and use as shown, 
> and `querky` will infer the required imports and place them in the generated file. 


## Query reuse

Since `querky` queries are simple f-strings, there is no limit to combining them together via CTEs or 
simply replacing a part of your query with another one. 

You can use subqueries as arguments to the main query with this technique:

```python
from querky import subquery


@qrk.query(shape='value', optional=False)
def add(a, b):
    return f"SELECT {+a}::INTEGER + {+b}"


@qrk.query(shape='value', optional=False)
def multiply(a, b):
    return f"SELECT {+a}::INTEGER * {+b}"


@qrk.query(shape='value', optional=False)
def divide(a, b):
    return f"SELECT {+a}::INTEGER / {+b}"


@qrk.query(shape='value', optional=False)
def operation(a, b):

    @subquery
    def add_ab():
        return add.query(a, b)

    @subquery
    def mult_ab():
        return multiply.query(a, b)

    return divide.query(add_ab, mult_ab)
```

The resulting SQL will be:

```sql
SELECT (SELECT $1::INTEGER + $2)::INTEGER / (SELECT $1::INTEGER * $2)
```

> We use `::INTEGER` cast to explicitly tell the database that in this query we work with integers. 
> Otherwise, query "compilation" will fail, because `+`, `-` and `/` operators exist for many types, 
> so there is no definitive way for the DBMS to infer what we meant.

If it's not enough for you, you can generate SQL by joining strings, 
the universal oldest method of how the ancients did it. 
Or use another library for this particular task.

Just remember that **the decorated function actually runs only once** to generate the SQL query. 
At runtime `querky` always uses that SQL query, never rerunning the function again. 
Except, of course, for explicit `Query#query(...)` calls, but these don't change `Query` state in any way.

> If you need query folding capabilities, e.g. `INSERT` a variable number of rows with a single query,
be sure to look into the `querky.tools.query_folder` module.

# How it Works

## The `Querky` class

It is the class to configure how the library will talk to the database and provide code generator configurations.

Let's go over constructor's arguments one by one:

### basedir

The absolute path to the base directory of your project. 

This path serves as an anchor, so that the generated files are placed properly. 

### annotation_generator

It's an instance of `AnnotationGenerator` subclass, which, well, generates annotations both for arguments and for return types,
based on `TypeKnowledge` collected. 

> It's safe to use the `ClassicAnnotationGenerator` for every use-case here.

### contract

This is an instance of `Contract` subclass. This `Contract` is between `querky` and your database driver of choice. 

The `Contract` describes a common interface for `querky` to talk to the database, execute your queries and infer the types. 

### conn_param_config

This directive tells `querky` where you want to place your database connection argument for every generated function.

Available subclasses: `First` and `Last`.

### type_factory

This function creates `one` and `many` queries' return types. The currently implemented types are under
`querky/type_constructors`. 

1. `TypedDictConstructor` - generates a subclass of [typing.TypedDict](https://docs.python.org/3/library/typing.html#typing.TypedDict). It's a regular dictionary with linter support.
2. `DataclassConstructor` - generates a class decorated with `@dataclasses.dataclass(...)`. Any additional `**kwargs` passed to `DataclassConstructor`'s constructor will be reflected in the decorator. E.g. `kw_only=True`, `slots=True`.

Every `TypeConstructor` has a `row_factory` argument, which should be provided in case your database driver does not return the expected type.

The `row_factory` is simply a converter from whatever the database driver returns to the type you need. 

> In this example, we convert native `asyncpg`'s `Record` objects to Python `dataclass`es.

> It is up to the user to implement `row_factory`.

### subdir

Name of the subdirectory, where all the generated files will go.

E.g., consider this project layout:

```
payment_service
|__ payments.py
|__ withdrawals.py
|__ __init__.py
delivery_service
|__ deliveries.py
|__ products.py
|__ __init__.py
```

Considering every `.py` file has queries and `subdir="queries"`, 
we're going to end up with the following structure:

```
payment_service
|__ queries
    |__ payment.py
    |__ withdrawal.py
|__ payment.py
|__ withdrawal.py
|__ __init__.py
delivery_service
|__ queries
    |__ delivery.py
    |__ product.py
|__ delivery.py
|__ product.py
|__ __init__.py
```

If not specified, files will be placed under the same directory as the source file, but with `_queries` postfix appended. 

The previously mentioned structure would become:

```
payment_service
|__ payment.py
|__ payment_queries.py
|__ withdrawal.py
|__ withdrawal_queries.py
|__ __init__.py
delivery_service
|__ delivery.py
|__ deliviry_queries.py
|__ product.py
|__ product_queries.py
|__ __init__.py
```

> You can change the naming behavior by overriding `Querky#generate_filename`.

## Custom Database Types

### [asyncpg](https://github.com/MagicStack/asyncpg) type_mapper

If you define custom types in your `postgres` database, 
you should also put conversions into the `AsyncpgNameTypeMapper` object using the `set_mapping` method, 
otherwise `querky` wouldn't know about them.

> `asyncpg`'s basic conversions are defined [here](https://magicstack.github.io/asyncpg/current/usage.html#type-conversion).

These are all available `asyncpg` default types:

```python
@qrk.query(shape='one', optional=False)
def all_default_types():
    return f'''
        SELECT
            NULL::INTEGER[] AS _anyarray,
            NULL::TSRANGE AS _anyrange,
            NULL::NUMMULTIRANGE AS _anymultirange,
            NULL::RECORD AS _record,
            NULL::VARBIT AS _bitstring,
            NULL::BOOL AS _bool,
            NULL::BOX AS _box,
            NULL::BYTEA AS _bytes,
            NULL::TEXT AS _text,
            NULL::CIDR AS _cidr,
            NULL::INET AS _inet,
            NULL::MACADDR AS _macaddr,
            NULL::CIRCLE AS _circle,
            NULL::DATE AS _date,
            NULL::TIME AS _time,
            NULL::TIME WITH TIME ZONE AS _timetz,
            NULL::INTERVAL AS _interval,
            NULL::FLOAT AS _float,
            NULL::DOUBLE PRECISION AS _double_precision,
            NULL::SMALLINT AS _smallint,
            NULL::INTEGER AS _integer,
            NULL::BIGINT AS _bigint,
            NULL::NUMERIC AS _numeric,
            NULL::JSON AS _json,
            NULL::JSONB AS _jsonb,
            NULL::LINE AS _line,
            NULL::LSEG AS _lseg,
            NULL::MONEY AS _money,
            NULL::PATH AS _path,
            NULL::POINT AS _point,
            NULL::POLYGON AS _polygon,
            NULL::UUID AS _uuid,
            NULL::TID AS _tid
        '''
```

```python
@dataclass(slots=True)
class AllDefaultTypes:
    _anyarray: list[int]
    _anyrange: _Range
    _anymultirange: list[_Range]
    _record: _Record
    _bitstring: _BitString
    _bool: bool
    _box: _Box
    _bytes: bytes
    _text: str
    _cidr: Union[IPv4Network, IPv6Network]
    _inet: Union[IPv4Interface, IPv6Interface, IPv4Address, IPv6Address]
    _macaddr: str
    _circle: _Circle
    _date: datetime.date
    _time: datetime.time
    _timetz: datetime.time
    _interval: datetime.timedelta
    _float: float
    _double_precision: float
    _smallint: int
    _integer: int
    _bigint: int
    _numeric: Decimal
    _json: str
    _jsonb: str
    _line: _Line
    _lseg: _LineSegment
    _money: str
    _path: _Path
    _point: _Point
    _polygon: _Polygon
    _uuid: UUID
    _tid: tuple
```


## Parameter Substitution

**`querky` never uses string concatenation to put arguments into a query. SQL injection is impossible.**

What it does instead is create a parametrized query based on your `Contract` (database driver) 
and your decorated function's signature. 

You can make sure by checking out any of your queries' `sql` field - 
it contains the actual SQL query that will always be used for this particular `Query` object.

The core of parameter substitution are the `ParamMapper` and `MappedParam` classes.

1. When a function is decorated with `@qrk.query`, it gets wrapped with a `Query` object.
2. The `Query` object in turn calls the function inside its `__init__` method with all arguments
substituted with `MappedParam` objects generated by your `Contract` backend's `ParamMapper` object. Each `ParamMapper` object is unique per query.  
3. The f-string gets run and the `MappedParam` objects "remember" the positions of the arguments inside the query.

After that the `ParamMapper` object is always ready to remap any incoming arguments into your database driver's format, since it knows the signature of the function, the order of arguments and which arguments they were.

## Query "compilation"

Once you run the `querky_gen.py` script, all the queries are `PREPARE`d against the DBMS to 
let it infer the types and check the correctness of the queries. 
You can call it a kind of "*compilation step*". 
Which, by the way, *conveniently checks query correctness before the program is run*, meaning, that if you have
a syntax error, the DBMS *itself* will tell you that, before you ship your code.


# Tips and Tricks
## Using ORM models for schema hinting

I personally found it very convenient to use ORM models to have 
a copy of the expected database schema state.

This way you can use the linter to your advantage when refactoring code: e.g. if a column gets dropped, 
the linter will be screaming "this field does not exist" for every query you used it in.

I suggest exploring the [sqlacodegen](https://github.com/agronholm/sqlacodegen) package to tackle the issue.

## Code generation is not required

`Query` objects are actually callable, if you look at the sample generated code. So, you don't need the code generation
procedure to use the argument mapping capabilities of this package.

# Issues, Help and Discussions

If you encountered an issue, you can leave it here, on GitHub.

If you want to join the discussion, there are Telegram chats:

- [English Language Chat 🇺🇸🇬🇧](https://t.me/querky_en)
- [Russian Language Chat 🇷🇺](https://t.me/querky_ru)

If you need to contact me personally:

- Email: `verolomnyy@gmail.com`
- Telegram: [@datscrazy](https://t.me/datscrazy)

# Licence

```
MIT License

Copyright (c) 2023 Andrei Karavatski
```