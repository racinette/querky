import functools
import pathlib
import ast


DEFAULT_ENCODING = "utf-8"


class ModuleInspector:
    def __init__(self, source_code: str):
        self.source_code = source_code
        self.module_ast = ast.parse(source_code)
        self.lines = source_code.splitlines(True)

    @classmethod
    def from_file(cls, filepath: str, encoding: str = DEFAULT_ENCODING):
        source_code = pathlib.Path(filepath).read_text(encoding)
        return cls(source_code)

    def get_func_header(self, fn: ast.FunctionDef):
        # находим начало
        if decorators := fn.decorator_list:
            last_decorator = decorators[-1]
            def_start_lineno = last_decorator.end_lineno
            assert isinstance(def_start_lineno, int)
        else:
            def_start_lineno = fn.lineno - 1

        # находим конец
        fn_end_lineno = fn.end_lineno
        assert isinstance(fn_end_lineno, int)

        fn_body_start_lineno = fn.body[0].lineno
        fn_body_end_lineno = fn.body[-1].end_lineno
        assert isinstance(fn_body_end_lineno, int)

        if fn_body_start_lineno == fn_body_end_lineno == fn_end_lineno:
            # конец сигнатуры, начало тела функции и ее конец
            # уместились на той же самой строчке
            fn_body_start_offset = fn.body[0].col_offset
        else:
            fn_body_start_offset = 0

        def_end_lineno = fn_body_start_lineno - 1
        lines = self.lines[def_start_lineno:def_end_lineno]
        last_line_index = len(lines) - 1
        lines[last_line_index] = lines[last_line_index][:def_end_lineno]
        header = "".join(lines)

        return header, (
            def_start_lineno + 1,
            def_end_lineno + 1,
            fn_body_start_offset,
        )

    def _get_func_w_lineno_in_header(self, lineno0: int):
        return self._get_func_w_lineno_in_header_inner(
            self.module_ast,
            lineno0
        )

    def _get_func_w_lineno_in_header_inner(
        self, base: ast.AST, lineno0: int
    ) -> tuple[ast.FunctionDef, str, tuple[int, int, int]]:
        for node in ast.iter_child_nodes(base):
            try:
                node_start_lineno: int = getattr(node, "lineno") - 1
                node_end_lineno: int = getattr(node, "end_lineno")
                assert isinstance(node_start_lineno, int)
                assert isinstance(node_end_lineno, int)
            except (AttributeError, AssertionError):
                continue
            else:
                if node_start_lineno <= lineno0 <= node_end_lineno:
                    if isinstance(node, ast.FunctionDef):
                        source_part, coordinates = self.get_func_header(node)
                        fn_header_start_lineno, fn_header_end_lineno, _ = (
                            coordinates
                        )
                        if (
                            fn_header_start_lineno
                            <= lineno0
                            <= fn_header_end_lineno
                        ):
                            return node, source_part, coordinates

                    return self._get_func_w_lineno_in_header_inner(
                        node, lineno0
                    )

        raise ValueError("function header not found")

    def get_return_annotation(self, lineno0: int):
        fn, func_def_source_part, coordinates = (
            self._get_func_w_lineno_in_header(lineno0)
        )
        fn_def_start_lineno = coordinates[0]
        returns = fn.returns
        if returns is None:
            raise ValueError(
                f"No return annotation found:\n"
                f"{enumerate_lines(
                    func_def_source_part,
                    start=fn_def_start_lineno
                )}"
            )

        return _ensure_hint(returns, self.source_code, lineno0)

    def get_arg_annotation(
        self, lineno0: int, argname: str
    ):
        fn, func_def_source_part, coordinates = (
            self._get_func_w_lineno_in_header(lineno0)
        )
        fn_def_start_lineno = coordinates[0]

        if fn.args.kwarg or fn.args.vararg:
            raise ValueError(
                "Query function cannot have *args and **kwargs "
                "in its signature. "
                "(kwarg and vararg arguments are forbidden):\n"
                f"{enumerate_lines(func_def_source_part, fn_def_start_lineno)}"
            )
        args = [*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs]
        for arg in args:
            if arg.arg == argname:
                annotation = arg.annotation
                if annotation is None:
                    raise ValueError(
                        f"{arg.arg} does not have an annotation:\n"
                        f"{enumerate_lines(
                            func_def_source_part,
                            fn_def_start_lineno
                        )}"
                    )

                return _ensure_hint(annotation, self.source_code, lineno0)

        raise ValueError(
            f"Unable to find argument named {argname} "
            "in function definition:\n"
            f"{enumerate_lines(func_def_source_part, fn_def_start_lineno)}"
        )

    def function_body_is_inline(self, fn: ast.FunctionDef):
        return function_body_is_inline(fn, self.source_code, self.lines)


def enumerate_lines(s: str, start: int = 1):
    lines = s.splitlines(True)
    max_line = start + len(lines)
    str_repr = str(max_line)
    str_repr_max_len = len(str_repr)
    enumerated_lines = [
        f"{str(idx + start).zfill(str_repr_max_len)}| {line}"
        for idx, line in enumerate(lines)
    ]
    return "".join(enumerated_lines)


def _ensure_hint(annotation: ast.expr, source_code: str, lineno0: int):
    hint = extract_hint(annotation)
    if hint is None:
        raise ValueError("No hint field found.")

    start = hint.lineno - 1
    end = hint.end_lineno
    assert end is not None

    if not (start <= lineno0 <= end):
        source_part = ast.get_source_segment(source_code, hint)
        assert source_part is not None
        raise ValueError(
            "Hint seems out of place:"
            f"expected line {lineno0 + 1}, but the hint is on "
            f"[{start + 1}, {end}] lines:\n",
            f"{enumerate_lines(source_part, start)}",
        )

    return hint


def extract_hint(annotation: ast.expr | None):
    if annotation is None:
        return
    if not isinstance(annotation, ast.Subscript):
        return
    annotated = annotation.slice
    if not isinstance(annotated, ast.Tuple):
        return
    if len(annotated.elts) < 2:
        return
    metadata = annotated.elts[1]
    if not isinstance(metadata, ast.Call):
        return
    for keyword in metadata.keywords:
        if keyword.arg == "hint":
            return keyword.value


def function_body_is_inline(
        fn: ast.FunctionDef,
        source_code: str,
        lines: list[str]
):
    target_line = fn.body[0].lineno - 1
    raw_line = lines[target_line].strip()
    segment = ast.get_source_segment(source_code, fn)
    assert segment is not None
    exact_line = segment.splitlines()[0].strip()
    return raw_line != exact_line
