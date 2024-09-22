import inspect
import typing
from dataclasses import dataclass

from querky.inspector import ModuleInspector


@dataclass(kw_only=True)
class InspectInfo:
    inspector: ModuleInspector
    lineno: int
    current_locals: dict[str, typing.Any]
    caller_file: str

    @property
    def lineno0(self):
        return self.lineno - 1


def get_inspect_info(level: int = 2):
    frameinfo = inspect.stack()[level]
    frame = frameinfo.frame
    traceback = inspect.getframeinfo(frame)

    try:
        locals_copy = {**frame.f_locals}
        lineno = frameinfo.lineno
        caller_file = traceback.filename
        inspector = ModuleInspector.cached_from_file(caller_file)

        return InspectInfo(
            inspector=inspector,
            lineno=lineno,
            current_locals=locals_copy,
            caller_file=caller_file,
        )
    finally:
        del frame
        del traceback
        del frameinfo
