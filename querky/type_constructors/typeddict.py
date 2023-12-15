from __future__ import annotations

import typing

from querky.common_imports import TYPING
from querky.type_constructor import TypeConstructor

if typing.TYPE_CHECKING:
    from querky.query import Query


class TypedDictConstructor(TypeConstructor[dict]):
    def __init__(
            self,
            query: Query,
            typename: str,
            row_factory: typing.Callable[[typing.Any], dict] | None
    ):
        super().__init__(query, typename, {TYPING}, row_factory)

    def generate_type_code(self) -> typing.Sequence[str] | None:
        self.type_code_generated = True
        lines = [
            f"class {self.typename}(typing.TypedDict):"
        ]
        for attr in self.attributes:
            lines.append(
                f"{self.indent(1)}{attr.name}: {attr.type_knowledge.typehint}"
            )
        return lines


__all__ = [
    "TypedDictConstructor"
]
