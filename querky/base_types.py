from __future__ import annotations

import typing
from inspect import Parameter
import inspect
from dataclasses import dataclass

from querky.attr import Attr
from querky.mixins import GetImportsMixin


@dataclass(slots=True, frozen=True)
class TypeMetaData(GetImportsMixin):
    counterpart: str
    required_imports: set[str] | None = None

    def get_imports(self) -> set[str]:
        if self.required_imports is None:
            return set()
        return set(self.required_imports)

    @classmethod
    def from_type(cls, t: typing.Type) -> TypeMetaData:
        type_name = t.__name__
        module_path = t.__module__
        return TypeMetaData(
            counterpart=type_name,
            required_imports={f"from {module_path} import {type_name}"}
        )


@dataclass
class TypeKnowledge(GetImportsMixin):
    metadata: TypeMetaData
    is_array: bool
    is_optional: bool | None
    elem_is_optional: bool | None = None
    typehint: str | None = None
    userhint: typing.Any | None = None
    required_imports: set[str] | None = None

    def __post_init__(self):
        self.set_userhint(self.userhint)

    def set_userhint(self, userhint: typing.Any):
        if userhint is None or userhint is inspect._empty:
            # пользователь не предоставил аннотацию
            return
        if userhint == typing.Optional:
            # пользователь явно указал, что этот аргумент опционален
            self.is_optional = True
        elif isinstance(userhint, str):
            # пользователь явно указал аннотацию - мы будем использовать ее прямо в таком же виде, как указано
            self.userhint = userhint
            self.typehint = self.userhint
        else:
            raise NotImplementedError(
                "Type annotation is a live object.\n"
                "It is impossible to copy safely between files.\n"
                "Placing it between parenthesis, thus making it a raw string, should do the trick.\n"
                "If you need to import something inside the generated file for this annotation to work, "
                "use `__imports__ = [<your imports as raw strings>]` in your source file."
            )

    def get_imports(self) -> set[str]:
        s = self.metadata.get_imports()
        if self.required_imports is not None:
            s.update(self.required_imports)
        return s

    def add_import(self, s: str) -> None:
        if self.required_imports is None:
            self.required_imports = set()
        self.required_imports.add(s)


@dataclass
class ResultAttribute(GetImportsMixin):
    index: int
    name: str
    type_knowledge: TypeKnowledge | None = None

    def consume_attr(self, attr: Attr) -> None:
        if attr.annotation is not None:
            self.type_knowledge.set_userhint(attr.annotation)
        elif attr.optional is not None:
            self.type_knowledge.is_optional = attr.optional

    def get_imports(self) -> set[str]:
        imports = self.type_knowledge.metadata.required_imports
        if not imports:
            return set()
        return set(imports)


class QuerySignature:
    def __init__(self, parameters: typing.Tuple[TypeKnowledge, ...], attributes: typing.Tuple[ResultAttribute, ...]):
        self.parameters = parameters
        self.attributes = attributes
