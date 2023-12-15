from __future__ import annotations

import typing

from asyncpg import Connection
from asyncpg.types import Attribute, Type

from querky.backends.postgresql.contract import PostgresqlContract
from querky.base_types import TypeMetaData, ResultAttribute, QuerySignature
from querky.backends.postgresql.dollar_sign_param_mapper import DollarSignParamMapper
from querky.backends.postgresql.type_mapper import PostgresqlTypeMapper
if typing.TYPE_CHECKING:
    from querky.query import Query


def _sync_not_implemented():
    raise NotImplementedError("there is no sync version of *async*pg, man")


class AsyncpgContract(PostgresqlContract):
    def __init__(self, type_mapper: PostgresqlTypeMapper):
        self.type_mapper = type_mapper

    def create_param_mapper(self, query: Query) -> DollarSignParamMapper:
        return DollarSignParamMapper(query)

    async def raw_execute(self, conn: Connection, sql: str, params):
        return await conn.execute(sql, *params)

    async def raw_fetchval(self, conn: Connection, sql: str, params):
        return await conn.fetchval(sql, *params)

    async def raw_fetchone(self, conn: Connection, sql: str, params):
        return await conn.fetchrow(sql, *params)

    async def raw_fetch(self, conn: Connection, sql: str, params):
        return await conn.fetch(sql, *params)

    async def raw_execute_sync(self, conn: Connection, sql: str, params):
        _sync_not_implemented()

    async def raw_fetchval_sync(self, conn, sql: str, params):
        _sync_not_implemented()

    async def raw_fetchone_sync(self, conn, sql: str, params):
        _sync_not_implemented()

    async def raw_fetch_sync(self, conn, sql: str, params):
        _sync_not_implemented()

    def get_default_record_type_metadata(self) -> TypeMetaData:
        return TypeMetaData('Record', {
            "from asyncpg import Record"
        })

    def get_connection_type_metadata(self) -> TypeMetaData:
        return TypeMetaData('Connection', {
            "from asyncpg import Connection"
        })

    async def get_query_signature(self, db: Connection, query: Query) -> QuerySignature:
        prepared_stmt = await db.prepare(query.sql)
        raw_params: typing.Tuple[Type, ...] = prepared_stmt.get_parameters()
        raw_attributes: typing.Tuple[Attribute, ...] = prepared_stmt.get_attributes()
        del prepared_stmt

        params = tuple(
            [
                await self.type_mapper.get_type_knowledge(self, db, param.oid)
                for param in raw_params
            ]
        )

        attributes = tuple(
            [
                ResultAttribute(index, attrib.name, await self.type_mapper.get_type_knowledge(self, db, attrib.type.oid))
                for attrib, index in zip(raw_attributes, range(len(raw_attributes)))
            ]
        )

        qs = QuerySignature(parameters=params, attributes=attributes)

        return qs

    def get_query_signature_sync(self, db, query: Query) -> QuerySignature:
        _sync_not_implemented()

    def is_async(self) -> bool:
        return True

    async def fetch_value(self, conn: Connection, query: Query, bound_params: typing.List):
        return await conn.fetchval(query.sql, *bound_params)

    async def fetch_one(self, conn: Connection, query: Query, bound_params: typing.List):
        return await conn.fetchrow(query.sql, *bound_params)

    async def fetch_all(self, conn: Connection, query: Query, bound_params: typing.List):
        return await conn.fetch(query.sql, *bound_params)

    async def fetch_column(self, conn: Connection, query: Query, bound_params: typing.List):
        rows = await conn.fetch(query.sql, *bound_params)
        return [row[0] for row in rows]

    async def fetch_status(self, conn: Connection, query: Query, bound_params: typing.List):
        return await conn.execute(query.sql, *bound_params)

    def fetch_value_sync(self, conn, query: Query, bound_params):
        _sync_not_implemented()

    def fetch_one_sync(self, conn, query: Query, bound_params):
        _sync_not_implemented()

    def fetch_all_sync(self, conn, query: Query, bound_params):
        _sync_not_implemented()

    def fetch_column_sync(self, conn, query: Query, bound_params):
        _sync_not_implemented()

    def fetch_status_sync(self, conn, query: Query, bound_params):
        _sync_not_implemented()
