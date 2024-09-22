import typing

from querky.typing_hints import (
    NoValue,
    _NoValue,
    StatusShape,
    ScalarShape,
    OneShape,
    ManyShape,
    ValueShape,
    ColumnShape,
    ResultShape,
    VectorShape,
)
from querky.inspect_helpers import get_inspect_info

if typing.TYPE_CHECKING:
    from querky.query import Query


class Param:
    def __init__(
        self, hint: typing.Any | None = None, addons: typing.Any | None = None
    ):
        # TODO:
        self._info = get_inspect_info()
        self.hint = hint
        self.addons = addons


class Return:
    @typing.overload
    def __init__(self, *, addons: typing.Any | None = None): ...

    @typing.overload
    def __init__(
        self,
        *,
        same_as: Query,
        shape: OneShape,
        optional: bool | None = None,
        addons: typing.Any | None = None,
    ): ...

    @typing.overload
    def __init__(
        self,
        *,
        same_as: Query,
        shape: ManyShape,
        addons: typing.Any | None = None,
    ): ...

    @typing.overload
    def __init__(
        self,
        *,
        same_as: Query,
        addons: typing.Any | None = None,
    ): ...

    @typing.overload
    def __init__(
        self,
        *,
        shape: OneShape,
        name: str | None = None,
        optional: bool = True,
        addons: typing.Any | None = None,
    ): ...

    @typing.overload
    def __init__(
        self,
        *,
        shape: ManyShape,
        name: str | None = None,
        addons: typing.Any | None = None,
    ): ...

    @typing.overload
    def __init__(
        self,
        *,
        shape: StatusShape,
        addons: typing.Any | None = None,
    ): ...

    @typing.overload
    def __init__(
        self,
        *,
        shape: ValueShape,
        optional: bool = True,
        addons: typing.Any | None = None,
    ): ...

    @typing.overload
    def __init__(
        self,
        *,
        shape: ColumnShape,
        optional: bool = False,
        addons: typing.Any | None = None,
    ): ...

    @typing.overload
    def __init__(
        self,
        *,
        shape: ScalarShape,
        hint: typing.Any,
        addons: typing.Any | None = None,
    ): ...

    def _is_empty(self, name: str) -> bool:
        val = getattr(self, name)
        return val is None or name == "_hint" and isinstance(val, NoValue)

    def _validate(
        self,
        context: str,
        *,
        required: set[str] | None = None,
        empty: set[str] | None = None,
    ):
        required = required or set()
        empty = empty or set()

        assert not required.intersection(empty)

        errors: list[str] = []

        for field in required:
            if self._is_empty(field):
                errors.append(f"{field} field must be set")

        for field in empty:
            if not self._is_empty(field):
                errors.append(f"{field} must be empty (not set)")

        if errors:
            raise ValueError("\n".join([context, *errors]))

    @property
    def same_as(self) -> Query:
        assert self._same_as is not None
        return self._same_as

    @property
    def shape(self) -> ResultShape:
        if self._shape is None:
            s = self.same_as.shape
        else:
            s = self._shape
        assert s in typing.get_args(ResultShape)
        return s  # type: ignore

    def __init__(self, **kwargs):
        self._info = get_inspect_info(kwargs.get("_stack_level", 2))
        self._same_as: typing.Optional[Query] = kwargs.get("same_as")
        self._hint = kwargs.get("hint", _NoValue)
        self._shape = kwargs.get("shape")
        self._optional = kwargs.get("optional")
        self._name = kwargs.get("name")

        self.addons = kwargs.get("addons")

        if self._same_as is not None:
            if (
                parent_shape := self.same_as.return_annotation.shape
            ) in typing.get_args(VectorShape):
                raise ValueError(
                    "same_as query must be a vector query "
                    "(shape must be equal to one or many)"
                )

            if self._shape == "many":
                self._validate(
                    "same_as with shape set to many",
                    empty={"_name", "_optional", "_hint"},
                )
            elif self._shape == "one":
                self._validate(
                    "same_as with shape set to one",
                    empty={"_name", "_hint"},
                )
            elif self._shape is None:
                empty = {"_name", "_hint"}

                if parent_shape == "many":
                    empty.add("_optional")

                self._validate(
                    "same_as with shape not set: "
                    f"defaulting to parent's shape={parent_shape}",
                    empty=empty,
                )
            else:
                raise ValueError(
                    f"cannot use {self._shape} with same_as query set"
                )
        else:
            if self._shape is None or self._shape == "status":
                self._shape = "status"
                self._validate(
                    "status shape: expect status message",
                    empty={"_hint", "_same_as", "_optional", "_name"},
                )
            elif self._shape == "one":
                self._validate("one shape: expect single row", empty={"_hint"})
                if self._optional is None:
                    self._optional = True
            elif self._shape == "many":
                self._validate(
                    "many shape: expect a list of rows",
                    empty={"_hint", "_optional"},
                )
            elif self._shape in typing.get_args(ScalarShape):
                self._validate(
                    "scalar shape: expect value or array of values",
                    empty={"_name"},
                )

                if self._is_empty("_hint"):
                    if self._shape == "value":
                        default_optional = True
                    else:
                        default_optional = False
                    if self._optional is None:
                        self._optional = default_optional
                else:
                    self._validate(
                        "scalar shape (type hint): "
                        "expect value or array of values",
                        empty={"_optional"},
                    )
            else:
                raise ValueError(f"wrong shape: {self._shape}")

        if not self._is_empty("_hint"):
            self._hint = self._info.inspector.get_return_annotation(
                self._info.lineno0
            )

    def annotate(self, query: Query) -> str:
        pass


__all__ = ["Return", "Param"]
