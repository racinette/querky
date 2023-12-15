from querky.base_types import TypeKnowledge, TypeMetaData
from querky.contract import Contract
from querky.backends.postgresql.type_mapper import PostgresqlTypeMapper


GET_PG_TYPE_SQL_QUERY = """
SELECT 
    oid::regtype::TEXT AS type_string, 
    typnamespace::regnamespace::TEXT AS namespace_string
FROM   
    pg_type
WHERE  
    oid = $1
"""


class PostgresqlNameTypeMapper(PostgresqlTypeMapper):
    def __init__(self, typemap: dict[str, dict[str, TypeMetaData]]):
        self.type_cache = dict()
        # копируем
        self.typemap = {
            schema_name: {
                type_name: type_metadata
                for type_name, type_metadata in schema_map.items()
            }
            for schema_name, schema_map in typemap.items()
        }

    def set_mapping(self, schema: str, type_name: str, metadata: TypeMetaData) -> None:
        if schema not in self.typemap:
            self.typemap[schema] = dict()
        s = self.typemap[schema]
        s[type_name] = metadata

    async def get_pg_type(self, contract: Contract, conn, oid: int):
        if (pg_type := self.type_cache.get(oid, None)) is None:
            pg_type = await contract.raw_fetchone(conn, GET_PG_TYPE_SQL_QUERY, (oid, ))
            self.type_cache[pg_type] = pg_type
        return pg_type

    def get_pg_type_sync(self, contract: Contract, conn, oid: int):
        if (pg_type := self.type_cache.get(oid, None)) is None:
            pg_type = contract.raw_fetchone_sync(conn, GET_PG_TYPE_SQL_QUERY, (oid, ))
            self.type_cache[pg_type] = pg_type
        return pg_type

    def get_type_knowledge_impl(self, pg_type) -> TypeKnowledge:
        basename: str = pg_type['type_string']
        schema: str = pg_type['namespace_string']

        is_array = basename.endswith("[]")
        if is_array:
            basename = basename[:-2]
        try:
            transforms = self.typemap[schema]
        except KeyError:
            raise KeyError(f"No transforms for schema: {schema} ({basename})")

        try:
            metadata = transforms[basename]
        except KeyError:
            raise KeyError(f"No metadata for type: {schema}.{basename} (array={is_array})")

        return TypeKnowledge(
            metadata,
            is_array=is_array,
            is_optional=None
        )

    async def get_type_knowledge(self, contract: Contract, conn, oid: int) -> TypeKnowledge:
        return self.get_type_knowledge_impl(await self.get_pg_type(contract, conn, oid))

    def get_type_knowledge_sync(self, contract: Contract, conn, oid: int) -> TypeKnowledge:
        return self.get_type_knowledge_impl(self.get_pg_type_sync(contract, conn, oid))
