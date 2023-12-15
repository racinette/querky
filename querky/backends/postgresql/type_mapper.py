from abc import ABC, abstractmethod

from querky.contract import Contract
from querky.base_types import TypeKnowledge


class PostgresqlTypeMapper(ABC):
    @abstractmethod
    async def get_type_knowledge(self, contract: Contract, conn, oid: int) -> TypeKnowledge:
        ...

    @abstractmethod
    def get_type_knowledge_sync(self, contract: Contract, conn, oid: int) -> TypeKnowledge:
        ...
