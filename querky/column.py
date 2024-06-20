from __future__ import annotations

import typing


class Column:
    def __init__(
        self, column_proxy_factory: ColumnProxyFactory, name: str
    ) -> None:
        self.column_proxy_factory = column_proxy_factory
        self.name = name
        self.hint = None
        self.optional = None
        self.transform = None

    def actual_hint(self):
        if self.hint is not None:
            return self.hint
        if self.transform is not None:
            return self.transform.__annotations__.get("return")
        return None

    def __call__(
        self,
        transform: typing.Optional[
            typing.Union[
                typing.Callable[[typing.Any, typing.Any], typing.Any],
                typing.Callable[[typing.Any], typing.Any],
            ]
        ] = None,
        *,
        hint: typing.Optional[str] = None,
        optional: typing.Optional[bool] = None,
    ) -> str:
        self.transform = transform
        self.hint = hint
        self.optional = optional
        self.column_proxy_factory.attrs.append(self)
        return self.name

    def __neg__(self) -> str:
        return self(optional=True)

    def __pos__(self) -> str:
        return self(optional=False)


class ColumnProxyFactory:
    def __init__(self):
        self.columns: typing.List[Column] = []

    def __getattr__(self, name: str) -> Column:
        return Column(self, name)

    def __getattrs__(self) -> typing.List[Column]:
        attrs = self.attrs
        self.attrs = []
        return attrs


column = ColumnProxyFactory()


__all__ = ["column", "Column"]
