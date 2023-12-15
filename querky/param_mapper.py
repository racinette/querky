from __future__ import annotations

import inspect
from inspect import Parameter
import typing
from abc import ABC, abstractmethod
from querky.exceptions import QueryInitializationError

if typing.TYPE_CHECKING:
    from querky.base_types import TypeKnowledge
    from querky.query import Query


M = typing.TypeVar('M', bound='MappedParam')


class MappedParam(ABC):
    def __init__(self, mapper: ParamMapper, pos: int, name: str, param: Parameter):
        self.mapper = mapper
        self.indices: list[int] = []
        self.pos = pos
        self.name = name
        self.param = param
        self.type_knowledge: TypeKnowledge | None = None

    def get_imports(self):
        if self.type_knowledge:
            return self.type_knowledge.get_imports()
        else:
            return set()

    @property
    def annotation_generator(self):
        return self.mapper.query.querky.annotation_generator

    def set_type_knowledge(self, tk: TypeKnowledge):
        try:
            tk.set_userhint(self.param.annotation)
            if self.param.default is None:
                # если пользователь выставил None по-умолчанию, то очевидно, что параметр опционален
                tk.is_optional = True
            self.annotation_generator.annotate(tk, "param")
            self.type_knowledge = tk
        except Exception as ex:
            raise QueryInitializationError(self.mapper.query, f"parameter `{self.name}`") from ex

    @abstractmethod
    def placeholder(self, current_index: int) -> str:
        ...

    def __pos__(self):
        curr = self.mapper.count
        self.indices.append(curr)
        self.mapper.count += 1
        return self.placeholder(curr)

    def __str__(self) -> str:
        return f'<{self.name}>'


class ParamMapper(typing.Generic[M]):
    def __init__(self, query: Query):
        self.query = query
        self.count = 0
        self.params: typing.List[M] = []
        self.positional: typing.List[M] = []
        self.keyword: typing.Dict[str, M] = dict()
        self.defaults: dict[str, typing.Any] = dict()

        for index, (name, param) in zip(range(len(query.sig.parameters)), query.sig.parameters.items()):
            param: Parameter
            if param.kind in [Parameter.VAR_KEYWORD, Parameter.VAR_POSITIONAL]:
                raise TypeError("Neither positional nor keyword varargs are supported")
            mapped_param = self.create_param(index, name, param)
            self.params.append(mapped_param)
            if param.kind in [Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD]:
                self.positional.append(mapped_param)
            elif param.kind == Parameter.KEYWORD_ONLY:
                self.keyword[name] = mapped_param
            else:
                raise NotImplementedError(param.kind)
            if param.default is not inspect._empty:
                self.defaults[name] = param.default

    @abstractmethod
    def assign_type_knowledge(self, t: typing.Tuple[TypeKnowledge, ...]):
        """
        Should be callin' set_type_knowledge on dem params.
        """
        ...

    def mirror_arguments(self) -> str:
        arr = []

        for arg in self.positional:
            arr.append(arg.name)
        for kwarg in self.keyword.keys():
            arr.append(f'{kwarg}={kwarg}')

        return ', '.join(arr)

    def parametrize_query(self) -> str:
        sql = self.query.query(*self.positional, **self.keyword)
        return sql

    @abstractmethod
    def map_params(self, *args, **kwargs):
        ...

    @abstractmethod
    def create_param(self, index: int, name: str, param: Parameter) -> M:
        ...
