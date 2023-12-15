from __future__ import annotations

import typing

from querky.common_imports import DATACLASS
from querky.type_constructor import TypeConstructor

if typing.TYPE_CHECKING:
    from querky.query import Query


class DataclassConstructor(TypeConstructor[typing.Any]):
    def __init__(
            self,
            query: Query,
            typename: str,
            row_factory: typing.Callable[[typing.Any], typing.Any] | None,
            **dataclass_kwargs
    ):
        self.dataclass_kwargs = dataclass_kwargs
        self.decorator = self.compile_decorator_string()
        super().__init__(query, typename, {DATACLASS}, row_factory=row_factory)

    def compile_decorator_string(self):
        kwargs = ', '.join([
            f'{argname}={argval}'
            for argname, argval in self.dataclass_kwargs.items()
        ])
        return f'@dataclass({kwargs})'

    def generate_type_code(self) -> typing.Optional[typing.List[str]]:
        self.type_code_generated = True
        lines = [
            self.decorator,
            f"class {self.typename}:"
        ]
        for attr in self.attributes:
            lines.append(
                f"{self.indent(1)}{attr.name}: {attr.type_knowledge.typehint}"
            )
        return lines
