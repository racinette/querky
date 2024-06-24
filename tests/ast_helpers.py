import ast

from querky.inspector import CodeBlock, code_block_types


DEFAULT_INDENT = "    "


def _list_code_block_nodes(
    node: ast.AST,
    parents: tuple[CodeBlock, ...],
    result: list[tuple[CodeBlock, ...]],
):
    if not isinstance(node, code_block_types):
        return
    new_parents = (*parents, node)
    result.append(new_parents)
    for child_node in ast.iter_child_nodes(node):
        _list_code_block_nodes(child_node, new_parents, result)


def list_body_nodes(node: ast.AST) -> list[tuple[CodeBlock, ...]]:
    result: list[tuple[CodeBlock, ...]] = []
    _list_code_block_nodes(node, (), result)
    return result


def _get_indent(
    node_path: tuple[ast.AST, ...], source_code_lines: list[str]
) -> str:
    a, b = node_path[-2], node_path[-1]
    a_lineno: int = getattr(a, "lineno") - 1
    b_lineno: int = getattr(b, "lineno") - 1
    a_col_offset: int = getattr(a, "col_offset")
    b_col_offset: int = getattr(b, "col_offset")

    a_line = source_code_lines[a_lineno]
    b_line = source_code_lines[b_lineno]

    a_indent = a_line[:a_col_offset]
    b_indent = b_line[:b_col_offset]

    a_len = len(a_indent)
    b_len = len(b_indent)
    return b_line[a_len:b_len]


def get_indent(
    node_paths: list[tuple[ast.AST, ...]], source_code_lines: list[str]
) -> str:
    longest_node_path = max(node_paths, key=lambda x: len(x))
    if len(longest_node_path) > 1:
        return _get_indent(longest_node_path, source_code_lines)
    else:
        return DEFAULT_INDENT


def chunk_split(s: str, length: int):
    string_length = len(s)
    if string_length % length != 0:
        raise ValueError(
            f"Cannot divide {string_length}-long string"
            f" evenly to {length}-long chunks."
        )
    chunks: list[str] = []
    for start in range(0, string_length, length):
        stop = start + length
        chunk = s[start:stop]
        chunks.append(chunk)
    return chunks


def get_indent_level(
    node: CodeBlock,
    source_code_lines: list[str],
    indent_value: str = DEFAULT_INDENT,
) -> int:
    if isinstance(node, ast.Module):
        return -1
    lineno = node.lineno - 1
    col_offset = node.col_offset
    curr_indent = source_code_lines[lineno][:col_offset]
    if not curr_indent:
        return 0
    indents = chunk_split(curr_indent, len(indent_value))
    for indent in indents:
        if indent != indent_value:
            raise ValueError(f"Unexpected indent value: `{indent}`")
    return len(indents)
