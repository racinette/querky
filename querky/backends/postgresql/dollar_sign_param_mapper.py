import typing
from inspect import Parameter

from querky.base_types import TypeKnowledge
from querky.param_mapper import ParamMapper, MappedParam, M
from querky.exceptions import QueryInitializationError


class DollarSignMappedParam(MappedParam):
    def placeholder(self, current_index: int) -> str:
        return f"${self.pos + 1}"


class DollarSignParamMapper(ParamMapper[DollarSignMappedParam]):
    def assign_type_knowledge(self, t: typing.Tuple[TypeKnowledge, ...]):
        if len(t) != len(self.params):
            raise QueryInitializationError(
                self.query,
                "Number of function signature parameters does not match "
                f"the actual number of arguments inside the query: {len(t)} vs {len(self.params)}"
            )
        for tk, param in zip(t, self.params):
            param: MappedParam
            tk: TypeKnowledge
            try:
                param.set_type_knowledge(tk)
            except Exception as ex:
                raise QueryInitializationError(
                    self.query,
                    f"Setting type knowledge to `{param.name}` raised an unexpected exception."
                ) from ex

    def map_params(self, *args, **kwargs):
        bound = self.query.sig.bind(*args, **kwargs)
        return [
            bound.arguments[param.name]
            for param in self.params
        ]

    def create_param(self, index: int, name: str, param: Parameter) -> M:
        return DollarSignMappedParam(self, index, name, param)
