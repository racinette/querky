import typing


class SubQuery:
    def __init__(self, q: typing.Callable[[], str]):
        self.query = q

    def __pos__(self) -> str:
        return f"({self.query()})"


def subquery(q: typing.Callable[[], str]) -> SubQuery:
    return SubQuery(q)


__all__ = [
    "subquery"
]
