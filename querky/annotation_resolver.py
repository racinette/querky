from __future__ import annotations

import typing
import types
import builtins
import abc

from querky.pyver import PYVER
from querky.import_resolver import climb_down_reference_tree

# AST parser with Type Inference!!!
# https://github.com/pylint-dev/astroid

# https://greentreesnakes.readthedocs.io/en/latest/


BUILTIN_REVERSE_LOOKUP = {
    varval: varname
    for varname, varval in builtins.__dict__.items()
    if not varname.startswith("_")
    and varname
    not in ["credits", "copyright", "license", "help", "exit", "quit"]
}


TYPING_TYPES = [
    typing._ProtocolMeta,
    typing._SpecialGenericAlias,
    typing._SpecialForm,
]

if PYVER >= (3, 11, 0):
    TYPING_TYPES.append(typing._AnyMeta)
if PYVER >= (3, 12, 0):
    TYPING_TYPES.append(typing._DeprecatedGenericAlias)

TYPING_REVERSE_LOOKUP = {
    varval: varname
    for varname, varval in typing.__dict__.items()
    if not varname.startswith("_") and isinstance(varval, tuple(TYPING_TYPES))
}


def istypevar(annotation: typing.Any) -> bool:
    return isinstance(annotation, typing.TypeVar)


class _ImpliedImport:
    def __init__(
        self,
        from_where: tuple[str, ...],
        import_what: str,
        access_what: tuple[str, ...],
    ):
        self.from_where = from_where
        self.import_what = import_what
        self.access_what = access_what


class _DisassembledType(abc.ABC):
    def __init__(
        self,
        base: _DisassembledType | None,
        context: typing.Any,
        annotation: typing.Any,
    ) -> types.NoneType:
        self.base = base
        self.context = context
        self.annotation = annotation

    @classmethod
    @abc.abstractmethod
    def isinstance(cls, annotation: typing.Any) -> bool: ...

    @classmethod
    def match_annotation(
        cls,
        base: _DisassembledType | None,
        context: typing.Any,
        annotation: typing.Any,
    ) -> _DisassembledType:
        """
        Аннотация -- это древовидная структура данных.
        Узлы:
        1. GenericAlias -- (no)
        2. Type
           1. builtin -- (no)
           2. custom -- (yes)
        3. (> Python 3.12) TypeAliasType -- (yes)
        4. Instance:
           1. Literal (str, int, etc.) -- (no)
           2. Object (Enum instance, etc.) -- (yes)

        Импортировать будем только узлы, отмеченные (yes),
        так как они могут (и должны) быть импортированы.

        Для остальных должны быть воссозданы
        эквивалентные объекты аннотаций.

        PS:
        Для GenericAlias'ов можно пробовать резолвить импорты.
        НО! Можно получать false-positives очень просто.

        Например,
            `assert typing.Tuple[int, float] is typing.Tuple[int, float]`,
            но
            `assert tuple[int, float] is not tuple[int, float]`.
        то есть:
            ```
            c = typing.Tuple[int, float]
            d = typing.Tuple[int, float]
            assert c is d
            ```
        Есть какая-то оптимизация на уровне typing модуля
        при создании аннотаций типов.
        К сожалению, это приглашает false-positive импорты
        из сторонних модулей,
        в которых есть такие же аннотации на уровне модуля.

        Например, мы определили алиас типа typing.Literal['yes', 'no'],
        и импортированный модуль определил такой же.
        CPython для него не сделает другого объекта,
        а выплюнет ТОТ ЖЕ ОБЪЕКТ для каждой встретившейся идентичной аннотации.
        Поэтому у нас нет возможности хоть как-то узнать,
        откуда именно был импортирован тот или иной алиас.
        Поэтому мы не будем даже пытаться,
        а будем генерировать эквивалентное определение типа
        в каждой использующей его аннотации.

        PPS:
        (Пока) Нерешаемые Проблемы:
        1. Не могу разделить инлайн определение
        от использования алиаса в Python < 3.12.
        2. Не могу резолвить дженерики -> нет возможности резолвить
        сложные дженерик конструкции.
        """
        types: list[type[_DisassembledType]] = [
            # TODO: _DisassembledType_Self,
            _DisassembledType_Typing,
            _DisassembledType_GenericAlias,
            _DisassembledType_BuiltinLiteral,
            _DisassembledType_BuiltinName,
            _DisassembledType_TypeAlias,
        ]
        for t in types:
            if t.isinstance(annotation):
                res = t(base, context, annotation)
                return res
        return _DisassembledType_RuntimeObject(base, context, annotation)

    @property
    def root(self) -> _DisassembledType:
        if self.base is None:
            return self
        else:
            return self.base.root

    def iterate_annotation_args(
        self, args, filt: typing.Callable[[typing.Any], bool] | None = None
    ):
        arr = []
        for arg in args:
            if isinstance(arg, list):
                nested_arr = self.iterate_annotation_args(arg, filt)
                arr.append(nested_arr)
            else:
                val = _DisassembledType.match_annotation(
                    self, self.context, arg
                )
                if not filt or filt(val):
                    arr.append(val)
        return arr


class _DisassembledType_Typing(_DisassembledType):
    def __init__(
        self,
        base: _DisassembledType | None,
        context: typing.Any,
        annotation: typing.Any,
    ) -> types.NoneType:
        self.origin = typing.get_origin(annotation)
        super().__init__(base, context, annotation)

    @classmethod
    def isinstance(cls, annotation: typing.Any) -> bool:
        origin = typing.get_origin(annotation)
        return origin in TYPING_REVERSE_LOOKUP

    @property
    def is_union(self):
        return self.origin is typing.Union

    def __repr__(self):
        if self.is_union:
            return ""
        return TYPING_REVERSE_LOOKUP[self.origin]


class _DisassembledType_GenericAlias(_DisassembledType):
    def __init__(
        self,
        base: _DisassembledType | None,
        context: typing.Any,
        annotation: typing.Any,
    ) -> types.NoneType:
        super().__init__(base, context, annotation)
        self._post_init(annotation)

    def _post_init(self, annotation: typing.Any):
        self.origin = typing.get_origin(annotation)
        if self.origin is None:
            raise ValueError(
                "Could not determine origin of a GenericAlias annotation"
            )
        self.origin_type = _DisassembledType.match_annotation(
            self, self.context, self.origin
        )
        if isinstance(self.origin_type, _DisassembledType_BuiltinLiteral):
            raise ValueError("Literal cannot be origin")
        self.args = typing.get_args(annotation)

        def filt(arg) -> bool:
            if istypevar(arg):
                raise NotImplementedError(
                    "Unable to resolve TypeVars for generic classes. "
                    f"Problem: {arg} in annotation {self.root}"
                )
            return True

        self.arg_types = self.iterate_annotation_args(self.args, filt)

    @classmethod
    def isinstance(cls, annotation: typing.Any) -> bool:
        if _GenericAlias := getattr(typing, "_GenericAlias"):
            return isinstance(annotation, (_GenericAlias, types.GenericAlias))
        return isinstance(annotation, types.GenericAlias)

    def _repr_args(self) -> str:
        arg_reprs = [repr(arg_type) for arg_type in self.arg_types]
        if getattr(self.origin_type, "is_union", False):
            joined_string = " | ".join(arg_reprs)
            return joined_string
        else:
            joined_string = ", ".join(arg_reprs)
            return f"[{joined_string}]"

    def __repr__(self):
        base = repr(self.origin_type)
        args = self._repr_args()
        return f"{base}{args}"


class _DisassembledType_BuiltinLiteral(_DisassembledType):
    @classmethod
    def isinstance(cls, annotation: typing.Any) -> bool:
        return type(annotation) in (bytes, str, int, float, types.NoneType)

    def __repr__(self):
        return repr(self.annotation)


class _DisassembledType_BuiltinName(_DisassembledType):
    @classmethod
    def isinstance(cls, annotation: typing.Any) -> bool:
        return annotation in BUILTIN_REVERSE_LOOKUP

    def __repr__(self):
        return BUILTIN_REVERSE_LOOKUP[self.annotation]


class _DisassembledType_TypeAlias(_DisassembledType_GenericAlias):
    @classmethod
    def isinstance(cls, annotation: typing.Any) -> bool:
        if PYVER >= (3, 12, 0):
            if isinstance(annotation, typing.TypeAliasType):
                return True
        # we won't be trying the trick of resolving
        # TypeAlias annotated variables
        # it's too hard: it requires both static and runtime analysis
        # AND it doesn't pay off that much
        return False

    def __init__(
        self,
        base: _DisassembledType | None,
        context: typing.Any,
        annotation: typing.Any,
    ) -> types.NoneType:
        super().__init__(base, context, annotation)
        self._post_init(annotation.__value__)


class _DisassembledType_RuntimeObject(_DisassembledType):
    @classmethod
    def isinstance(cls, annotation: typing.Any) -> bool:
        return True


class AnnotationDisassembler:
    def __init__(self):
        pass

    @classmethod
    def disassemble(cls, annotation: typing.Any, context: typing.Any):

        d = _DisassembledType.match_annotation(None, context, annotation)
        return d
