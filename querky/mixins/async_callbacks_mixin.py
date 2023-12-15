from __future__ import annotations

from logging import getLogger
import typing
import inspect
from collections import defaultdict


logger = getLogger("querky")


MaybeAsyncCallback = typing.Callable[[...], typing.Any | typing.Awaitable]
CallbackTuple = tuple[MaybeAsyncCallback, int, bool]


class CallbackContext:
    __slots__ = (
        "base",
        "when",
        "key",
        "execute",
        "remove",
        "replaced"
    )

    def __init__(
            self,
            base: AsyncCallbacksMixin,
            when: str,
            key: str,
            execute: MaybeAsyncCallback,
            remove: bool,
            replaced: bool
    ):
        self.base = base
        self.key = key
        self.when = when
        self.execute = execute
        self.remove = remove
        self.replaced = replaced

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.remove:
            self.base.off(self.when, self.key)


class AsyncCallbacksMixin:
    def __init__(self, *events: str):
        if events:
            self._callbacks: dict[str, dict[str, CallbackTuple]] = {
                event: dict()
                for event in events
            }
        else:
            self._callbacks: dict[str, dict[str, CallbackTuple]] = defaultdict(lambda: dict())

    async def trigger(self, __when: str, *args, **kwargs) -> None:
        when = self._callbacks[__when]
        callbacks = [
            (k, v[0], v[1], v[2])
            for k, v in when.items()
        ]
        # highest priority first
        callbacks.sort(key=(lambda x: x[2]), reverse=True)
        for key, callback, priority, critical in callbacks:
            try:
                val = callback(*args, **kwargs)
                if inspect.iscoroutine(val):
                    await val
            except Exception as ex:
                logger.exception(
                    "Exception occurred while handling %s callback (%s).",
                    __when, key
                )
                if critical:
                    raise ex

    def off(self, when: str, key: str) -> MaybeAsyncCallback | None:
        callbacks = self._callbacks[when]
        try:
            return callbacks.pop(key)[0]
        except KeyError:
            return None

    def has(self, when: str, key: str) -> bool:
        return key in self._callbacks[when]

    def priority(self, when: str, key: str) -> int | None:
        w = self._callbacks[when]
        if key in w:
            return w[key][1]
        return None

    def on(
            self,
            when: str,
            key: str,
            execute: MaybeAsyncCallback,
            *,
            on_conflict: typing.Literal['replace', 'ignore', 'raise'] = 'ignore',
            context: bool = False,
            priority: int = 0,
            critical: bool = False
    ) -> CallbackContext | bool:
        if self.has(when, key):
            if on_conflict == 'replace':
                self._callbacks[when][key] = (execute, priority, critical)
                if context:
                    return CallbackContext(self, when, key, execute, remove=True, replaced=True)
                return True
            elif on_conflict == 'raise':
                raise KeyError(key)
            else:
                if context:
                    return CallbackContext(self, when, key, execute, remove=False, replaced=False)
                return False
        else:
            self._callbacks[when][key] = (execute, priority, critical)
            if context:
                return CallbackContext(self, when, key, execute, remove=True, replaced=False)
            return True


__all__ = [
    "AsyncCallbacksMixin"
]
