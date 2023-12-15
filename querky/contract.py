from __future__ import annotations

import typing
from abc import ABC, abstractmethod

from querky.base_types import TypeMetaData
if typing.TYPE_CHECKING:
    from querky.query import Query
    from querky.param_mapper import ParamMapper
    from querky.base_types import QuerySignature


class Contract(ABC):
    @abstractmethod
    def create_param_mapper(self, query: Query) -> ParamMapper:
        ...

    @abstractmethod
    def get_default_record_type_metadata(self) -> TypeMetaData:
        ...

    @abstractmethod
    def get_connection_type_metadata(self) -> TypeMetaData:
        ...

    @abstractmethod
    async def get_query_signature(self, db, query: Query) -> QuerySignature:
        ...

    @abstractmethod
    def get_query_signature_sync(self, db, query: Query) -> QuerySignature:
        ...

    @abstractmethod
    def is_async(self) -> bool:
        ...

    @abstractmethod
    async def fetch_value(self, conn, query: Query, bound_params):
        ...

    @abstractmethod
    async def fetch_one(self, conn, query: Query, bound_params):
        ...

    @abstractmethod
    async def fetch_all(self, conn, query: Query, bound_params):
        ...

    @abstractmethod
    async def fetch_column(self, conn, query: Query, bound_params):
        ...

    @abstractmethod
    async def fetch_status(self, conn, query: Query, bound_params):
        ...

    @abstractmethod
    async def raw_execute(self, conn, sql: str, params):
        ...

    @abstractmethod
    async def raw_fetchval(self, conn, sql: str, params):
        ...

    @abstractmethod
    async def raw_fetchone(self, conn, sql: str, params):
        ...

    @abstractmethod
    async def raw_fetch(self, conn, sql: str, params):
        ...

    @abstractmethod
    def fetch_value_sync(self, conn, query: Query, bound_params):
        ...

    @abstractmethod
    def fetch_one_sync(self, conn, query: Query, bound_params):
        ...

    @abstractmethod
    def fetch_all_sync(self, conn, query: Query, bound_params):
        ...

    @abstractmethod
    def fetch_column_sync(self, conn, query: Query, bound_params):
        ...

    @abstractmethod
    def fetch_status_sync(self, conn, query: Query, bound_params):
        ...

    @abstractmethod
    async def raw_execute_sync(self, conn, sql: str, params):
        ...

    @abstractmethod
    async def raw_fetchval_sync(self, conn, sql: str, params):
        ...

    @abstractmethod
    def raw_fetchone_sync(self, conn, sql: str, params):
        ...

    @abstractmethod
    def raw_fetch_sync(self, conn, sql: str, params):
        ...

