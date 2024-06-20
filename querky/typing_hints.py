import typing

from querky.query_param import QueryParam


OneShape = typing.Literal["one"]
ManyShape = typing.Literal["many"]
VectorShape = typing.Literal[OneShape, ManyShape]
ValueShape = typing.Literal["value"]
ColumnShape = typing.Literal["column"]
ScalarShape = typing.Literal[ValueShape, ColumnShape]
OptionalShape = typing.Literal[OneShape, ValueShape, ColumnShape]
TypeShape = typing.Literal[VectorShape, ScalarShape]
StatusShape = typing.Literal["status"]
ResultShape = typing.Literal[TypeShape, StatusShape]


class NoValue:
    pass


class QueryDef(typing.Protocol):
    __name__: str

    def __call__(self, *args: QueryParam, **kwargs: QueryParam) -> str: ...


_NoValue = NoValue()


__all__ = ["ResultShape", "NoValue", "_NoValue", "QueryDef"]
