from __future__ import annotations
from abc import ABC, abstractmethod

import typing

from querky.base_types import TypeKnowledge, TypeMetaData
from querky.mixins import GetImportsMixin
from querky.exceptions import QueryInitializationError
from querky.base_types import ResultAttribute

if typing.TYPE_CHECKING:
    from querky.query import Query


class ResultShape(ABC, GetImportsMixin):
    def __init__(self, query: Query) -> None:
        self.query: Query = query
        self.return_type: TypeKnowledge | None = None

    @property
    def querky(self):
        return self.query.querky

    def get_imports(self) -> set[str]:
        return self.return_type.get_imports()

    @abstractmethod
    def set_attributes(self, attrs: typing.Tuple[ResultAttribute, ...]):
        ...

    @abstractmethod
    def generate_type_code(self) -> typing.List[str] | None:
        ...

    def get_annotation(self) -> str:
        return self.return_type.typehint

    @abstractmethod
    async def fetch(self, conn, bound_params):
        ...

    @abstractmethod
    async def fetch_sync(self, conn, bound_params):
        ...

    @abstractmethod
    def get_exports(self) -> typing.Sequence[str]:
        ...


class Value(ResultShape):
    def __init__(self, query: Query, annotation: str | TypeMetaData | None = None, *, optional: bool = False):
        super().__init__(query)
        self.annotation = annotation
        self.attribute: ResultAttribute | None = None
        self.optional = optional

    def set_attributes(self, attrs: tuple[ResultAttribute, ...]):
        if len(attrs) != 1:
            raise TypeError(
                f"{self.query.string_signature()}\n"
                f"Query is declared to return a single attribute, but it returns: {len(attrs)}."
            )
        attr = attrs[0]
        if isinstance(self.annotation, TypeMetaData):
            type_knowledge = TypeKnowledge(
                metadata=self.annotation,
                is_array=False,
                is_optional=self.optional
            )
            self.attribute = ResultAttribute(
                name=attr.name,
                index=attr.index,
                type_knowledge=type_knowledge
            )
        else:
            self.attribute = attr
            type_knowledge = self.attribute.type_knowledge
            type_knowledge.typehint = self.annotation
            type_knowledge.is_optional = self.optional
        self.return_type = type_knowledge
        self.annotate()

    def annotate(self):
        self.query.annotation_generator.annotate(self.return_type, 'attribute')

    def generate_type_code(self) -> typing.List[str] | None:
        return None

    async def fetch(self, conn, bound_params):
        contract = self.query.module.querky.contract
        return await contract.fetch_value(conn, self.query, bound_params)

    def fetch_sync(self, conn, bound_params):
        contract = self.query.module.querky.contract
        return contract.fetch_value_sync(conn, self.query, bound_params)

    def get_exports(self) -> typing.Sequence[str]:
        return []


def value_(annotation: str | TypeMetaData | None = None, *, optional: bool = False) -> typing.Callable[[Query], ResultShape]:
    def late_binding(query: Query) -> Value:
        return Value(query, annotation, optional=optional)
    return late_binding


class Column(Value):
    def __init__(self, query: Query, annotation: str | TypeMetaData | None = None, *, elem_optional: bool = True):
        super().__init__(query, annotation, optional=False)
        self.elem_optional = elem_optional

    def set_attributes(self, attrs: typing.Tuple[ResultAttribute, ...]):
        super().set_attributes(attrs)
        type_knowledge = self.attribute.type_knowledge
        type_knowledge.is_array = True
        type_knowledge.is_optional = False
        type_knowledge.elem_is_optional = self.elem_optional
        self.query.annotation_generator.annotate(self.return_type, 'attribute')

    def annotate(self):
        pass

    async def fetch(self, conn, params):
        contract = self.query.module.querky.contract
        return await contract.fetch_column(conn, self.query, params)

    def fetch_sync(self, conn, params):
        contract = self.query.module.querky.contract
        return contract.fetch_column_sync(conn, self.query, params)


def column_(annotation: str | TypeMetaData | None = None, *, elem_optional: bool = False) -> typing.Callable[[Query], ResultShape]:
    def late_binding(query: Query) -> Value:
        return Column(query, annotation, elem_optional=elem_optional)
    return late_binding


class One(ResultShape):
    def __init__(self, query: Query, typename: str | None, *, optional: bool = True):
        super().__init__(query)

        if self.query.parent_query is None:
            if self.querky.type_factory is not None:
                self.ctor = self.querky.type_factory(self.query, typename)
            else:
                self.ctor = None
        else:
            # забираем конструктор типа из базового запроса
            parent_shape = self.query.parent_query.shape
            if not isinstance(parent_shape, (All, One)):
                raise ValueError("Invalid shape, must be a row shape")

            self.ctor = parent_shape.ctor
            # копируем название типа из отеческого запроса
            typename = parent_shape.ctor.typename

        if self.ctor.shape is None:
            self.ctor.shape = self

        self.optional = optional
        if self.ctor is not None:
            type_meta = TypeMetaData(typename)
        else:
            type_meta = self.query.contract.get_default_record_type_metadata()
        self.return_type = TypeKnowledge(
            metadata=type_meta,
            is_optional=self.optional,
            is_array=False,
            elem_is_optional=None
        )
        self.annotate()

    def annotate(self):
        self.query.annotation_generator.annotate(self.return_type, context='result_type')

    def set_attributes(self, attrs: typing.Tuple[ResultAttribute, ...]):
        for attribute in self.query.query_signature.attributes:
            try:
                if attr_hint := self.query.attr_hints.get(attribute.name, None):
                    attribute.consume_attr(attr_hint)
                self.query.annotation_generator.annotate(attribute.type_knowledge, 'attribute')
            except Exception as ex:
                raise QueryInitializationError(self.query, f"attribute `{attribute.name}`") from ex
        if self.ctor is not None:
            if self.ctor.attributes is None:
                self.ctor.set_attributes(attrs)
            elif self.ctor.attributes != attrs:
                raise QueryInitializationError(
                    self.query,
                    "Expected the same return type signature, but the attributes are not equal:\n"
                    f"Expected: {self.ctor.attributes}\n"
                    f"Got: {attrs}"
                )

    def generate_type_code(self) -> typing.List[str] | None:
        if self.ctor is not None and not self.ctor.type_code_generated:
            return self.ctor.generate_type_code()
        else:
            return None

    def get_imports(self) -> set[str]:
        s = super().get_imports()
        if self.ctor is not None:
            return s.union(self.ctor.get_imports())
        return s

    async def fetch(self, conn, params):
        contract = self.query.module.querky.contract
        row = await contract.fetch_one(conn, self.query, params)
        if self.ctor.row_factory and row is not None:
            row = self.ctor.row_factory(row)
        return row

    def fetch_sync(self, conn, params):
        contract = self.query.module.querky.contract
        row = contract.fetch_one_sync(conn, self.query, params)
        if self.ctor.row_factory:
            row = self.ctor.row_factory(row)
        return row

    def get_exports(self) -> typing.Sequence[str]:
        if self.ctor is not None:
            return [self.ctor.get_exported_name()]
        else:
            return []


def one_(typename: str | None, *, optional: bool = True) -> typing.Callable[[Query], ResultShape]:
    def late_binding(query: Query) -> One:
        return One(query, typename, optional=optional)
    return late_binding


class All(One):
    def __init__(self, query: Query, typename: str | None,):
        super().__init__(query, typename, optional=False)
        self.return_type.is_optional = False
        self.return_type.is_array = True
        self.return_type.elem_is_optional = False
        self.query.annotation_generator.annotate(self.return_type, context='result_type')

    def annotate(self):
        pass

    async def fetch(self, conn, params):
        contract = self.query.module.querky.contract
        rows = await contract.fetch_all(conn, self.query, params)
        if self.ctor.row_factory:
            rows = [
                self.ctor.row_factory(row)
                for row in rows
            ]
        return rows

    def fetch_sync(self, conn, params):
        contract = self.query.module.querky.contract
        rows = contract.fetch_all_sync(conn, self.query, params)
        if self.ctor.row_factory:
            rows = [
                self.ctor.row_factory(row)
                for row in rows
            ]
        return rows


def all_(typename: str | None) -> typing.Callable[[Query], ResultShape]:
    def late_binding(query: Query) -> All:
        return All(query, typename)
    return late_binding


class Status(ResultShape):
    def get_annotation(self) -> str:
        return 'str'

    def generate_type_code(self) -> typing.List[str] | None:
        return None

    def get_imports(self) -> set[str]:
        return set()

    async def fetch(self, conn, bound_params):
        contract = self.query.module.querky.contract
        return await contract.fetch_status(conn, self.query, bound_params)

    def fetch_sync(self, conn, bound_params):
        contract = self.query.module.querky.contract
        return contract.fetch_status(conn, self.query, bound_params)

    def set_attributes(self, attr: typing.Tuple[ResultAttribute, ...]):
        pass

    def get_exports(self) -> typing.Sequence[str]:
        return []


def status_() -> typing.Callable[[Query], ResultShape]:
    def late_binding(query: Query) -> Status:
        return Status(query)
    return late_binding


__all__ = [
    "ResultShape",
    "Value",
    "value_",
    "Column",
    "column_",
    "One",
    "one_",
    "All",
    "all_",
    "Status",
    "status_",
]
