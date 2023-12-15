from __future__ import annotations

import typing


class Attr:
    def __init__(self, attr_proxy: AttrProxy, name: str) -> None:
        self.attr_proxy = attr_proxy
        self.name = name
        self.annotation = None
        self.optional = None

    def __call__(self, annotation: typing.Optional[str] = None, *, optional: typing.Optional[bool] = None) -> str:
        self.annotation = annotation
        self.optional = optional
        self.attr_proxy.attrs.append(self)
        return self.name

    def __neg__(self) -> str:
        return self(optional=True)

    def __pos__(self) -> str:
        return self(optional=False)


class AttrProxy:
    def __init__(self):
        self.attrs: typing.List[Attr] = []

    def __getattr__(self, name: str) -> Attr:
        return Attr(self, name)

    def __getattrs__(self) -> typing.List[Attr]:
        attrs = self.attrs
        self.attrs = []
        return attrs


attr = AttrProxy()


__all__ = [
    "attr",
    "Attr"
]
