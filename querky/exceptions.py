from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    from querky.query import Query


class QueryInitializationError(Exception):
    def __init__(self, query: Query, additional_hint: str | None = None) -> None:
        self.message = f"{query.string_signature()}:\n{query.sql}"
        if additional_hint is not None:
            self.message += f"\n{additional_hint}"
        super().__init__(self.message)

