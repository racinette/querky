from __future__ import annotations

import typing
from dataclasses import dataclass
from inspect import Parameter

from querky.base_types import TypeKnowledge, TypeMetaData
if typing.TYPE_CHECKING:
    from querky.query import Query


@dataclass(slots=True, frozen=True, kw_only=True)
class ConnParamConfig:
    name: str

    def create_parameter(
            self,
            query: Query,
            parameters: typing.Sequence[Parameter],
            type_metadata: TypeMetaData
    ) -> tuple[Parameter, TypeKnowledge, int]:
        ...


@dataclass(slots=True, frozen=True, kw_only=True)
class First(ConnParamConfig):
    positional: bool = False

    def create_parameter(
            self,
            _query: Query,
            parameters: typing.Sequence[Parameter],
            type_metadata: TypeMetaData
    ) -> tuple[Parameter, TypeKnowledge, int]:
        if self.positional:
            kind = Parameter.POSITIONAL_ONLY
        else:
            if parameters and parameters[0].kind == Parameter.POSITIONAL_ONLY:
                kind = Parameter.POSITIONAL_ONLY
            else:
                kind = Parameter.POSITIONAL_OR_KEYWORD

        p = Parameter(self.name, kind)
        return p, TypeKnowledge(type_metadata, False, False, False), 0


@dataclass(slots=True, frozen=True, kw_only=True)
class Last(ConnParamConfig):
    keyword: bool = False

    def create_parameter(
            self,
            _query: Query,
            parameters: typing.Sequence[Parameter],
            type_metadata: TypeMetaData
    ) -> tuple[Parameter, TypeKnowledge, int]:
        if self.keyword:
            kind = Parameter.KEYWORD_ONLY
        else:
            if parameters and parameters[-1].kind == Parameter.KEYWORD_ONLY:
                kind = Parameter.KEYWORD_ONLY
            else:
                kind = Parameter.POSITIONAL_OR_KEYWORD

        p = Parameter(self.name, kind)

        return p, TypeKnowledge(type_metadata, False, False, False), len(parameters)


__all__ = [
    "ConnParamConfig",
    "First",
    "Last"
]
