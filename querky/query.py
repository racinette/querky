from __future__ import annotations

import inspect
from inspect import Parameter
from os import path
import typing

from querky.logger import logger
from querky.exceptions import QueryInitializationError
from querky.helpers import ReprHelper, DictGetAttr
from querky.base_types import TypeKnowledge, QuerySignature
from querky.annotated import Return, Param
from querky.query_param import ParamMapper
from querky.column import column, Column as ColumnHint
from querky.typing_hints import QueryDef
from querky.result_shape import (
    Value,
    Column,
    Status,
    Many,
    One,
    ResultShape,
)

if typing.TYPE_CHECKING:
    from querky.module_constructor import ModuleConstructor


class Query:

    def __init__(
        self,
        func: QueryDef,
        param_annotations: typing.Dict[str, Param],
        return_annotation: typing.Optional[Return],
        module: ModuleConstructor,
        explicit_name: typing.Optional[str],
    ) -> None:
        if return_annotation is None:
            return_annotation = Return()

        self.param_annotations = param_annotations
        self.return_annotation = return_annotation

        self.imports = set()
        self.query = func
        self.name = explicit_name or func.__name__

        self.sig = inspect.signature(func)
        self.template_signature = None

        self.module = module
        self.module.queries_list.append(self)

        self.param_mapper: ParamMapper = self.contract.create_param_mapper(
            self
        )
        self.sql = self.param_mapper.parametrize_query()
        self.default = DictGetAttr(self.param_mapper.defaults)
        # side effect: attr gets populated, so we flush it
        self.column_hints: dict[str, ColumnHint] = {
            a.name: a for a in column.__getattrs__()
        }

        module_filename = self.module.module.__file__

        assert module.querky.basedir is not None, "basedir must not be None"
        assert module_filename is not None, "module_filename must not be None"

        common = path.commonprefix([module.querky.basedir, module_filename])
        relative_path_length = len(common)
        self.relative_path = module_filename[relative_path_length:]
        self.unique_name = f"{self.relative_path}:{self.query.__name__}"
        self.local_name = self.get_local_name()

        self._query_signature: QuerySignature | None = None
        self.conn_type_knowledge: TypeKnowledge | None = None

        self.bound_type = None

        self.shape = shape

        if not isinstance(self.shape, (One, Many)) and self.parent_query:
            raise ValueError(
                "Only One and Many queries can have a parent query."
            )
        if self.parent_query and not isinstance(
            self.parent_query.shape, (One, Many)
        ):
            raise ValueError(
                "Parent query must be of either One or All shape."
            )

        logger.debug("Query: %s\nSQL: %s", self.unique_name, self.sql)

    def _make_result_shape(self) -> ResultShape:
        assert self.return_annotation is not None

        if self.return_annotation.shape == "status":
            shape = Status(self)
        elif self.return_annotation.shape == "value":
            # TODO: что делать с TypeMetaData?? надо думать...
            shape = Value(self)
        elif self.return_annotation.shape == "column":
            pass
        elif self.return_annotation.shape == "one":
            pass
        elif self.return_annotation.shape == "many":
            pass
        else:
            raise NotImplementedError(self.return_annotation.shape)

        if not isinstance(self.shape, (One, Many)) and self.parent_query:
            raise ValueError(
                "Only One and Many queries can have a parent query."
            )
        if self.parent_query and not isinstance(
            self.parent_query.shape, (One, Many)
        ):
            raise ValueError(
                "Parent query must be of either One or All shape."
            )

    @property
    def conn_param_config(self):
        return self.querky.conn_param_config

    @property
    def annotation_generator(self):
        gen = self.querky.annotation_generator
        assert gen is not None
        return gen

    @property
    def contract(self):
        contract = self.module.querky.contract
        assert contract is not None
        return contract

    @property
    def querky(self):
        return self.module.querky

    @property
    def has_parent(self):
        return (
            self.return_annotation is not None
            and self.return_annotation.same_as is not None
        )

    @property
    def query_signature(self):
        assert self._query_signature is not None
        return self._query_signature

    @property
    def parent_query(self):
        assert (
            anno := self.return_annotation
        ) is not None, "must have return annotation set"
        assert (
            parent := anno.same_as
        ) is not None, "parent query must not be None"
        return parent

    @property
    def parent_shape(self):
        parent_query = self.parent_query
        parent_shape = parent_query.shape
        assert isinstance(
            parent_shape, (One, Many)
        ), "parent shape must be ether One or Many"
        return parent_shape

    @property
    def parent_shape_ctor(self):
        ctor = self.parent_shape.ctor
        assert ctor is not None, "parent shape must have a constructor"
        return ctor

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
        self.param_mapper.assign_type_knowledge(
            self.query_signature.parameters
        )
        # а типы аттрибутов - результату
        self.shape.set_attributes(self.query_signature.attributes)

    async def fetch_types(self, db) -> None:
        try:
            self._query_signature = await self.contract.get_query_signature(
                db, self
            )
            self._after_types_fetched()
        except QueryInitializationError:
            raise
        except Exception as ex:
            raise QueryInitializationError(
                self, additional_hint="fetching types"
            ) from ex

    def fetch_types_sync(self, db) -> None:
        try:
            self._query_signature = self.contract.get_query_signature_sync(
                db, self
            )
            self._after_types_fetched()
        except QueryInitializationError:
            raise
        except Exception as ex:
            raise QueryInitializationError(
                self, additional_hint="fetching types"
            ) from ex

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
                        f"{param.name}: parameter type annotation is missing",
                    )

                new_params.append(
                    Parameter(
                        name,
                        old_param.kind,
                        annotation=ReprHelper(typehint),
                        default=default,
                    )
                )

            conn_param, type_knowledge, index = (
                self.conn_param_config.create_parameter(
                    self,
                    new_params,
                    self.contract.get_connection_type_metadata(),
                )
            )
            self.conn_type_knowledge = type_knowledge
            self.annotation_generator.annotate(
                type_knowledge, context="conn_param"
            )
            if type_knowledge.typehint is not None:
                conn_param = conn_param.replace(
                    annotation=ReprHelper(type_knowledge.typehint)
                )

            new_params.insert(index, conn_param)

            return_annotation = self.shape.get_annotation()
            if return_annotation is None:
                raise QueryInitializationError(
                    self, "return type annotation is missing"
                )

            return_annotation_repr = ReprHelper(return_annotation)

            self.new_signature = self.sig.replace(
                parameters=new_params, return_annotation=return_annotation_repr
            )

            is_async = self.contract.is_async()
            async_ = "async " if is_async else ""
            await_ = "await " if is_async else ""
            _sync = "_sync" if not is_async else ""

            conn_str = self.conn_param_config.name

            arg_remap_string = self.param_mapper.mirror_arguments()
            args = f"{conn_str}, {arg_remap_string}"
            ident = self.querky.get_indent(1)
            fname = self.local_name

            try:
                code = [
                    f"{async_}def {self.name}{self.new_signature}:",
                    f"{ident}return {await_}{fname}.execute{_sync}({args})",
                ]
            except Exception as _ex:  # noqa: F841
                # for debugging
                raise

            logger.debug("[OK] - %s", self.unique_name)
            return code
        except Exception as ex:
            logger.exception("[BAD] - %s", self.unique_name)
            raise ex

    def get_type_bind_ident(self) -> typing.Optional[str]:
        if isinstance(self.shape, (Value, Column, Status)):
            return None
        elif isinstance(self.shape, (One, Many)):
            if self.shape.ctor:
                return self.shape.ctor.typename
            return None

    def get_exports(self):
        exports = {self.name, *self.shape.get_exports()}
        if parent := self.parent_query:
            parent_shape = parent.shape
            assert isinstance(
                parent_shape, (One, Many)
            ), "parent shape must be ether One or Many"
            ctor = parent_shape.ctor
            assert ctor is not None, "parent shape must have a constructor"
            exports.add(ctor.typename)
        return exports

    def get_imports(self):
        imports = set(self.imports)
        for elem in self.param_mapper.params:
            imports.update(elem.get_imports())

        if self.conn_type_knowledge is not None:
            imports.update(self.conn_type_knowledge.get_imports())

        if self.has_parent and self.parent_query.module is not self.module:
            imports.add(
                f"from {self.parent_query.module.module_path} "
                f"import {self.parent_shape_ctor.typename}"
            )
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
            lines.append("")
            lines.append("")

        # proxy function code, which simply accepts annotated arguments
        # and proxies the call to this query
        func_code = self._generate_proxy_function_code()
        if cb := self.module.querky.on_before_func_code_emit:
            func_code = cb(func_code, self)
        lines.extend(func_code)

        if bound_type_ident := self.get_type_bind_ident():
            # binding return type to the underlying query
            lines.append("")
            lines.append(f"{self.local_name}.bind_type({bound_type_ident})")

        return lines

    def __call__(self, conn, *args, **kwargs):
        if self.contract.is_async():
            return self.execute(conn, *args, **kwargs)
        else:
            return self.execute_sync(conn, *args, **kwargs)
