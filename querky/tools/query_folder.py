from __future__ import annotations

import typing
from typing import Tuple, Sequence, List, TypeVar


PSQL_QUERY_ALLOWED_MAX_ARGS = 32767


T = TypeVar('T')
PlaceholderGenerator = typing.Generator[str, None, None]


def dollar_sign(start_at: int = 1) -> PlaceholderGenerator:
    def gen_dollar_sign():
        i = start_at

        while True:
            yield f'${i}'
            i += 1

    return gen_dollar_sign()


def question_mark() -> PlaceholderGenerator:
    def gen_question_mark():
        while True:
            yield '?'

    return gen_question_mark()


def percent_placeholder() -> PlaceholderGenerator:
    def gen_percent_placeholder():
        while True:
            yield '%s'

    return gen_percent_placeholder()


class FoldArgs:
    def __init__(
            self,
            tuple_len: int,
            tmpl: str,
            delim: str = ',',
            placeholder: typing.Callable[[], PlaceholderGenerator] = dollar_sign,
            batch_length: int = PSQL_QUERY_ALLOWED_MAX_ARGS,
            enable_cache: bool = False
    ):
        """
        :param tuple_len: length of a single tuple.
        :param batch_length: maximum number of arguments per batch. Postgres caps at 32767.
        :param tmpl: template into which the tuples will be inserted.
        :param delim: delimiter between template occurrences
        :param placeholder:
        :param enable_cache:
                     enables cache on all operations.
                     Will boost performance in case there is frequent usage of the same number of tuples per template.
                     Otherwise, it will clog up the memory, so use carefully.
        """

        self.placeholder = placeholder
        self.enable_cache = enable_cache
        if tuple_len < 1:
            raise ValueError()
        self.tuple_len = tuple_len
        self.delim = delim
        self.tmpl = tmpl
        self.batch_length = batch_length
        self.tuples_count_per_batch = self.batch_length // self.tuple_len
        if self.tuples_count_per_batch < 1:
            raise ValueError(f"cannot fit a single tuple ({self.tuple_len}) with query capacity ({self.batch_length})")
        # cache
        self.args_cache: dict[int, Tuple[int, ...]] = dict()
        self.fold_cache: dict[int, Tuple[str, ...]] = dict()
        self.values_cache: dict[int, str] = dict()

    def _create_values(self, n: int) -> str:
        if (res := self.values_cache.get(n, None)) is None:
            p = self.placeholder()
            batch = []
            for _ in range(n):
                tuple_repr = self.tmpl.format(
                    *[
                        next(p)
                        for _ in range(self.tuple_len)
                    ]
                )
                batch.append(tuple_repr)
            res = self.delim.join(batch)
            if n == self.tuples_count_per_batch or self.enable_cache:
                self.values_cache[n] = res
        return res

    def args(self, tuples: Sequence[Sequence[T, ...]]) -> List[List[T]]:
        args_batches = []
        for tuples_count in self.batch_tuples(len(tuples)):
            args = []
            batch = tuples[:tuples_count]
            for t in batch:
                if len(t) != self.tuple_len:
                    raise ValueError(f"tuples must all have {self.tuple_len} (got: {len(t)}): {t}")
                args.extend(t)
            args_batches.append(args)
            tuples = tuples[tuples_count:]
        return args_batches

    def batch_tuples(self, n: int) -> Tuple[int, ...]:
        if (res := self.args_cache.get(n, None)) is None:
            arr = []
            while n > 0:
                tuples_len = min(n, self.tuples_count_per_batch)
                arr.append(tuples_len)
                n -= tuples_len
            res = tuple(arr)
            if self.enable_cache:
                self.args_cache[n] = res
        return res

    def fold(self, n: int) -> Tuple[str, ...]:
        if (res := self.fold_cache.get(n, None)) is None:
            arr: List[str] = []
            for count in self.batch_tuples(n):
                values = self._create_values(count)
                arr.append(values)
            res = tuple(arr)
            if self.enable_cache:
                self.fold_cache[n] = res
        return res


class FoldedQuery:
    def __init__(
            self,
            sql: str,
            tuple_len: int,
            tmpl: str | None = None,
            delim: str = ',',
            placeholder: typing.Callable[[], PlaceholderGenerator] = dollar_sign,
            batch_length: int = PSQL_QUERY_ALLOWED_MAX_ARGS,
            enable_cache: bool = False,
            sql_format_key: str = 'folded'
    ):
        if tmpl is None:
            tmpl = ','.join(['{}' for _ in range(tuple_len)])
            tmpl = f'({tmpl})'
        self.enable_cache = enable_cache
        self.sql_format_key = sql_format_key
        self.sql = sql
        self.fold_args = FoldArgs(
            tuple_len=tuple_len,
            tmpl=tmpl,
            delim=delim,
            enable_cache=enable_cache,
            placeholder=placeholder,
            batch_length=batch_length
        )
        self.query_cache: dict[int, tuple[str]] = dict()

    def create_queries(self, tuples_count: int) -> tuple[str]:
        if not (queries := self.query_cache.get(tuples_count, None)):
            q = []
            values = self.fold_args.fold(tuples_count)
            for v in values:
                q.append(
                    self.sql.format(**{self.sql_format_key: v})
                )
            queries = tuple(q)
            if self.enable_cache:
                self.query_cache[tuples_count] = queries
        return queries

    def __call__(self, tuples: typing.Sequence[typing.Tuple]) -> typing.Tuple[typing.Tuple[str], typing.List[typing.List]]:
        queries = self.create_queries(len(tuples))
        args = self.fold_args.args(tuples)
        return queries, args


__all__ = [
    "FoldArgs",
    "FoldedQuery"
]
