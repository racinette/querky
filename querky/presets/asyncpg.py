import types
import typing

from querky import Querky, Query
from querky.annotation_generators import ClassicAnnotationGenerator
from querky.backends.postgresql.asyncpg import AsyncpgContract
from querky.backends.postgresql.asyncpg.name_type_mapper import AsyncpgNameTypeMapper
from querky.type_constructors import DataclassConstructor, TypedDictConstructor
from querky.type_constructor import TypeConstructor


TypeFactoryPreset = typing.Literal[
    'typed_dict',
    'fake_dict',
    'dataclass',
    'dataclass+slots'
]


def use_preset(
        basedir: str,
        *,
        type_factory: TypeFactoryPreset | typing.Callable[[Query, str], TypeConstructor] = 'typed_dict',
        new_style_typehints: bool = True,
        **kwargs
):
    annotation_generator = ClassicAnnotationGenerator(new_style_typehints=new_style_typehints)

    type_mapper = AsyncpgNameTypeMapper()
    contract = AsyncpgContract(type_mapper=type_mapper)

    if isinstance(type_factory, str):
        if type_factory.startswith('dataclass'):
            slots = type_factory.endswith('+slots')

            def type_factory(query: Query, typename: str) -> TypeConstructor:
                def row_factory(record) -> typing.Any:
                    return query.bound_type(*tuple(record))

                return DataclassConstructor(
                    query,
                    typename,
                    row_factory=row_factory,
                    slots=slots
                )
        elif type_factory == 'typed_dict':

            def type_factory(query: Query, typename: str) -> TypeConstructor:
                def row_factory(record) -> dict:
                    return dict(record)

                return TypedDictConstructor(
                    query,
                    typename,
                    row_factory=row_factory,
                )

        elif type_factory == 'fake_dict':

            def type_factory(query: Query, typename: str) -> TypeConstructor:
                if query.kwargs.get('dict', False):
                    row_factory = dict
                else:
                    row_factory = None

                return TypedDictConstructor(query, typename, row_factory)

        else:
            raise NotImplementedError(type_factory)

    qrk = Querky(
        basedir=basedir,
        annotation_generator=annotation_generator,
        contract=contract,
        type_factory=type_factory,
        **kwargs
    )

    return qrk


async def generate(qrk: Querky, *args, base_modules: tuple[types.ModuleType, ...] | None = None, **kwargs):
    import asyncpg

    conn = await asyncpg.connect(*args, **kwargs)
    try:
        async with conn.transaction():
            await qrk.generate(conn, base_modules=base_modules)
    finally:
        await conn.close()


__all__ = [
    "use_preset",
    "generate"
]
