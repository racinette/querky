from __future__ import annotations

import inspect
from inspect import Parameter
from os import path
import typing

from querky.logger import logger
from querky.exceptions import QueryInitializationError
from querky.helpers import ReprHelper, DictGetAttr
from querky.base_types import TypeKnowledge, QuerySignature
from querky.conn_param_config import ConnParamConfig
from querky.param_mapper import ParamMapper
from querky.attr import attr as _attr_, Attr
from querky.result_shape import Value, Column, Status, All, One, ResultShape
if typing.TYPE_CHECKING:
    from querky.module_constructor import ModuleConstructor


RS = typing.TypeVar('RS', bound='ResultShape')


class Query(typing.Generic[RS]):
    defaults: dict[str, typing.Any]

    def __init__(
            self,
            func: typing.Callable,
            shape: typing.Callable[[Query], RS],
            module: ModuleConstructor,
            conn_param_config: ConnParamConfig,
            explicit_name: typing.Optional[str],
            parent_query: typing.Optional[Query[One | All]],
            kwargs: typing.Optional[typing.Dict[str, typing.Any]]
    ) -> None:
        self.parent_query: Query[One | All] | None = parent_query

        self.imports = set()
        self.kwargs = kwargs or dict()
        self.query = func
        self.name = explicit_name or func.__name__
        self.conn_param_config = conn_param_config

        self.sig = inspect.signature(func)
        self.template_signature = None

        self.module = module
        self.module.queries_list.append(self)

        self.param_mapper: ParamMapper = self.contract.create_param_mapper(self)
        self.sql = self.param_mapper.parametrize_query()
        self.default = DictGetAttr(self.param_mapper.defaults)
        # side effect: attr gets populated, so we flush it
        self.attr_hints: dict[str, Attr] = {
            a.name: a
            for a in _attr_.__getattrs__()
        }

        module_filename = self.module.module.__file__
        common = path.commonprefix([module.querky.basedir, module_filename])
        self.relative_path = module_filename[len(common):]
        self.unique_name = f"{self.relative_path}:{self.query.__name__}"
        self.local_name = self.get_local_name()

        self.query_signature: QuerySignature | None = None
        self.conn_type_knowledge: TypeKnowledge | None = None

        self.bound_type = None
        self.shape: ResultShape = shape(self)

        if not isinstance(self.shape, (One, All)) and parent_query:
            raise ValueError("Only One and All queries can have a parent query.")
        if parent_query and not isinstance(parent_query.shape, (One, All)):
            raise ValueError("Parent query must be of either One or All shape.")

        logger.debug(
            "Query: %s\nSQL: %s",
            self.unique_name, self.sql
        )

    @property
    def annotation_generator(self):
        return self.querky.annotation_generator

    @property
    def contract(self):
        return self.module.querky.contract

    @property
    def querky(self):
        return self.module.querky

    def bind_type(self, t) -> None:
        self.bound_type = t

    async def execute(self, conn, *args, **kwargs):
        params = self.param_mapper.map_params(*args, **kwargs)
        return await self.shape.fetch(conn, params)

    def execute_sync(self, conn, *args, **kwargs):
        params = self.param_mapper.map_params(*args, **kwargs)
        return self.shape.fetch_sync(conn, params)

    def _after_types_fetched(self):
        # типы параметров передадим мапперу
        self.param_mapper.assign_type_knowledge(self.query_signature.parameters)
        # а типы аттрибутов - результату
        self.shape.set_attributes(self.query_signature.attributes)

    async def fetch_types(self, db) -> None:
        try:
            self.query_signature = await self.contract.get_query_signature(db, self)
            self._after_types_fetched()
        except QueryInitializationError:
            raise
        except Exception as ex:
            raise QueryInitializationError(self, additional_hint="fetching types") from ex

    def fetch_types_sync(self, db) -> None:
        try:
            self.query_signature = self.contract.get_query_signature_sync(db, self)
            self._after_types_fetched()
        except QueryInitializationError:
            raise
        except Exception as ex:
            raise QueryInitializationError(self, additional_hint="fetching types") from ex

    def string_signature(self):
        return f"{self.relative_path}: {self.query.__name__}{self.sig}"

    def get_local_name(self) -> str:
        return f"_q{self.module.queries_list.index(self)}"

    def _generate_proxy_function_code(self):
        try:
            new_params = []

            for param in self.param_mapper.params:
                name = param.name

                old_param = param.param

                if old_param.default is not inspect._empty:
                    default = ReprHelper(f"{self.local_name}.default.{name}")
                else:
                    default = inspect._empty

                typehint = param.type_knowledge.typehint
                if typehint is None:
                    raise QueryInitializationError(
                        self,
                        f"{param.name}: parameter type annotation is missing"
                    )

                new_params.append(
                    Parameter(
                        name,
                        old_param.kind,
                        annotation=ReprHelper(typehint),
                        default=default
                    )
                )

            conn_param, type_knowledge, index = self.conn_param_config.create_parameter(
                self,
                new_params,
                self.contract.get_connection_type_metadata()
            )
            self.conn_type_knowledge = type_knowledge
            self.annotation_generator.annotate(type_knowledge, context='conn_param')
            if type_knowledge.typehint is not None:
                conn_param = conn_param.replace(annotation=ReprHelper(type_knowledge.typehint))

            new_params.insert(index, conn_param)

            return_annotation = self.shape.get_annotation()
            if return_annotation is None:
                raise QueryInitializationError(
                    self,
                    f"return type annotation is missing"
                )

            return_annotation_repr = ReprHelper(return_annotation)

            self.new_signature = self.sig.replace(
                parameters=new_params,
                return_annotation=return_annotation_repr
            )

            is_async = self.contract.is_async()
            async_ = 'async ' if is_async else ''
            await_ = 'await ' if is_async else ''
            _sync = "_sync" if not is_async else ''

            conn_str = self.conn_param_config.name

            arg_remap_string = self.param_mapper.mirror_arguments()
            arg_string = f"{conn_str}, {arg_remap_string}"

            try:
                code = [
                    f"{async_}def {self.name}{self.new_signature}:",
                    f"{self.querky.get_indent(1)}return {await_}{self.local_name}.execute{_sync}({arg_string})"
                ]
            except Exception as _ex:
                # for debugging
                raise

            logger.debug('[OK] - %s', self.unique_name)
            return code
        except Exception as ex:
            logger.exception('[BAD] - %s', self.unique_name)
            raise ex

    def get_type_bind_ident(self) -> typing.Optional[str]:
        if isinstance(self.shape, (Value, Column, Status)):
            return None
        elif isinstance(self.shape, (One, All)):
            if self.shape.ctor:
                return self.shape.ctor.typename
            return None

    def get_exports(self):
        exports = {
            self.name,
            *self.shape.get_exports()
        }
        if parent := self.parent_query:
            parent_shape = parent.shape
            if not isinstance(parent_shape, (One, All)):
                raise ValueError("parent shape must be ether One or All")
            shape: typing.Union[One, All] = parent_shape
            exports.add(shape.ctor.typename)
        return exports

    def get_imports(self):
        imports = set(self.imports)
        for elem in self.param_mapper.params:
            imports.update(elem.get_imports())

        if self.conn_type_knowledge is not None:
            imports.update(self.conn_type_knowledge.get_imports())

        if (parent := self.parent_query) and parent.module is not self.module:
            parent_shape = parent.shape
            if isinstance(parent_shape, (One, All)):
                imports.add(
                    f"from {parent.module.module_path} import {parent_shape.ctor.typename}"
                )
            else:
                raise ValueError("you can only use return types from 'one' and 'many' queries")
        else:
            # we're gonna create the type from scratch, so we need the imports
            imports.update(self.shape.get_imports())

        return imports

    def generate_code(self):
        lines = []
        # data type code
        if type_code := self.shape.generate_type_code():
            if cb := self.module.querky.on_before_type_code_emit:
                type_code = cb(type_code, self)
            lines.extend(type_code)
            lines.append('')
            lines.append('')

        # proxy function code, which simply accepts annotated arguments and proxies the call to this query
        func_code = self._generate_proxy_function_code()
        if cb := self.module.querky.on_before_func_code_emit:
            func_code = cb(func_code, self)
        lines.extend(func_code)

        if bound_type_ident := self.get_type_bind_ident():
            # binding return type to the underlying query
            lines.append('')
            lines.append(f'{self.local_name}.bind_type({bound_type_ident})')

        return lines

    def __call__(self, conn, *args, **kwargs):
        if self.contract.is_async():
            return self.execute(conn, *args, **kwargs)
        else:
            return self.execute_sync(conn, *args, **kwargs)
