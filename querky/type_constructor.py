from __future__ import annotations

import typing

from querky.base_types import ResultAttribute
from querky.mixins import GetImportsMixin

if typing.TYPE_CHECKING:
    from querky.query import Query
    from querky.result_shape import ResultShape


T = typing.TypeVar('T')


class TypeConstructor(typing.Generic[T], GetImportsMixin):
    def __init__(
            self,
            query: Query,
            typename: str,
            required_imports: typing.Set[str],
            row_factory: typing.Callable[[typing.Any], T] | None
    ):
        self.query = query
        self.type_code_generated = False
        self.typename = typename
        self.required_imports = required_imports
        self.shape: typing.Optional[ResultShape] = None
        self.attributes: typing.Optional[typing.Tuple[ResultAttribute, ...]] = None
        self.row_factory = row_factory
        self.type_code_generated: bool = False
        self.attributes_collected: bool = False

    def set_attributes(self, attrs: typing.Tuple[ResultAttribute, ...]):
        self.attributes = attrs

    def get_imports(self) -> set[str]:
        s = set(self.required_imports)
        for attr in self.attributes:
            s.update(attr.get_imports())
        return s

    def get_exported_name(self) -> str:
        return self.typename

    def indent(self, i: int) -> str:
        return self.shape.query.querky.get_indent(i)
