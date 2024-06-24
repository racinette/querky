from random import Random
import glob
import os
from pathlib import Path
import textwrap
import ast
from querky.inspector import (
    extract_hint,
    ModuleInspector,
    body_is_inline,
)

from tests.static_env import SOURCECODE_DIRECTORY
from tests.ast_helpers import (
    get_indent_level,
    list_body_nodes,
    DEFAULT_INDENT,
)


SEED = 123
random = Random(SEED)
TEST_QUERKY_SIGNATURES: list[str] = [
    """def some_query(
    user_id: typing.Annotated[MappedParam, Param(hint=UserId)]
) -> Annotated[str, Return(shape="value", hint=UserInfo | None)]:""",
    """def fetch_account_ids_with_balance_gt(
    balance_gt: Annotated[MappedParam, Param(hint=PositiveInteger)],
    registered_after: Annotated[MappedParam, Param(
        hint=datetime | None
    )],
) -> Annotated[
    str,
    Return(
        shape="column",
        hint=AccountId  # TODO: validation
    )
]:""",
    ###
    """def fetch_operations_data(
    status: Annotated[
        MappedParam,
        Param(
            hint=OperationStatusEnum
        )
    ], /,
    # random comment
    # multiline
    created_after: Annotated[
        MappedParam,  # <--
        Param(hint=datetime | None)  # TODO:
        # ok..
    ],

) -> Annotated[
    str,
    Return(hint=OperationData,
           shape="column",
    )
]:""",
    ###
    """def summarize_daily_profits(
    since_date: Annotated[MappedParam,
                          Param(hint=datetime | None)],
    only_profits_gt: Annotated[MappedParam, Param(
        hint=Decimal | None
    )], *, include_weekdays: Annotated[MappedParam, Param(hint=list[typing.Literal[
            'mo',  # monday, etc.
            'tu',
            # will put comment here
            'we', 'th', 'fr',
            'sa', 'su']] | None)]  # weekdays????
) -> Annotated[str, Return(
    hint=(Decimal  # comment here
          | int
          | float
          # what what??
          | None
          ), shape="column")]:""",
    ###
    """def insert_user(username: Annotated[MappedParam, Param(
        hint=Username
    )], /, *, phone_number: Annotated[MappedParam, Param(hint=PhoneNumber | None)], auth_method: typing.Annotated[MappedParam,
        Param(hint=(
            typing.Literal[
                # pasha verni stenu
                "telegram",
                # gamer gurlzz
                "discord",  # TODO:
                # boring
                "email",
                # ooooooo
                "google"
            ]
        ))
]) -> typing.Annotated[str, Return(hint=(
    UserId  # tashkent
))]:""",
    ###
    """def fetch_user_unique_transaction_receivers(user_id: Annotated[MappedParam, Param(hint=UserId)], after_ts: Annotated[MappedParam, Param(hint=datetime | int | None)]) -> Annotated[str, Annotated[Return(shape="column", hint=Username)]]:""",
]
TEST_DECORATORS: list[str] = [
    "@random_decorator",
    "@test_decorator(1, 2, 3)",
    '@decorated_stuff(a=1, b="cool")',
    """@multiline(
    some_arg1="long argument string",
    dict_arg={
        "a": 1,
        "b": 2,
        "c": 3
    }
)""",
    """@test_dec([
    SomeObject(),
    SomeObject(),
    SomeObject(),
    SomeObject()
])""",
]
TEST_BODY_LINES = [
    'var1: str = "some value"',
    "var2: int = 1 + 2",
    "some_boolean: bool = False",
    "empty_value = None",
    "def fn(): ...",
    "print(123)",
    'show_me_the_body = "Death Sounds"',
]


def _extract_annotated_hints(fn: ast.FunctionDef):
    args = fn.args

    assert not args.kwarg
    assert not args.vararg

    arg_list = [
        *args.posonlyargs,
        *args.args,
        *args.kwonlyargs,
    ]
    hints: dict[str, ast.expr | None] = dict()

    for arg in arg_list:
        arg_name = arg.arg
        val = extract_hint(arg.annotation)
        hints[arg_name] = val
    hints["return"] = extract_hint(fn.returns)

    hints_only = {
        key: value for key, value in hints.items() if value is not None
    }

    return hints_only


def _extract_hints(source_code: str):
    source_code += f"\n{DEFAULT_INDENT}pass"
    module_ast = ast.parse(source_code)
    func = module_ast.body[0]
    assert isinstance(func, ast.FunctionDef)
    hints = _extract_annotated_hints(func)
    return hints


SIGNATURE_HINTS: dict[str, dict[str, ast.expr]] = {
    signature: _extract_hints(signature)
    for signature in TEST_QUERKY_SIGNATURES
}


def _fill_signature(s: str) -> tuple[str, int]:
    tag = "####### HIDE'N'SEEK #######"
    lines = [tag, "@qrk.query"]
    offset = len(lines)
    if random.random() > 0.5:
        count = random.randint(1, len(TEST_DECORATORS))
        decorators = [random.choice(TEST_DECORATORS) for _ in range(count)]
        for decorator in decorators:
            offset += decorator.count("\n") + 1
        lines.extend(decorators)
    lines.append(s)
    body_type_decision = random.random()
    if body_type_decision < 0.2:
        lines[-1] += " ..."
    elif body_type_decision < 0.4:
        lines.append(DEFAULT_INDENT + "...")
    elif body_type_decision < 0.6:
        lines.append(DEFAULT_INDENT + "pass")
    else:
        loc = [*TEST_BODY_LINES]
        random.shuffle(loc)
        for n in range(0, random.randint(1, len(TEST_BODY_LINES))):
            lines.append(DEFAULT_INDENT + loc[n])
    lines.append(tag)
    lines.append("")
    return "\n".join(lines), offset


def test_hint_hide_n_seek():
    """
    We take all the source code and sprinkle @qrk.query
    functions randomly over the file contents.
    This way we test raw string type annotation extraction.
    """
    p = os.path.join(SOURCECODE_DIRECTORY.rstrip("/") + "/**/*.py")
    python_scripts = glob.glob(p, recursive=True)
    assert len(python_scripts) > 0
    for python_script in python_scripts:
        source_code = Path(python_script).read_text()
        source_code_lines = source_code.splitlines(True)
        module_ast = ast.parse(source_code)
        body_nodes = list_body_nodes(module_ast)

        if len(body_nodes) == 1:
            continue

        assert len(body_nodes) > 0
        for signature in TEST_QUERKY_SIGNATURES:
            signature_hints = SIGNATURE_HINTS[signature]
            for node_path in body_nodes:
                parent_node = node_path[-1]
                if body_is_inline(parent_node, source_code, source_code_lines):
                    # лучше не трогать инлайны, реально
                    continue

                indent_level = get_indent_level(parent_node, source_code_lines)
                next_indent_level = indent_level + 1
                next_indent = DEFAULT_INDENT * next_indent_level
                signature_variation, offset = _fill_signature(signature)
                indented_signature = textwrap.indent(
                    signature_variation, next_indent
                )
                target_node = random.choice(parent_node.body)
                new_source_code_lines = [*source_code_lines]

                insert_at_line = target_node.lineno - 1

                new_source_code_lines.insert(
                    insert_at_line, indented_signature
                )
                new_source_code = "".join(new_source_code_lines)

                m = ModuleInspector(new_source_code)

                for name, hint in signature_hints.items():
                    hint_lineno0 = insert_at_line + hint.lineno + offset
                    if name == "return":
                        found_hint = m.get_return_annotation(hint_lineno0)
                    else:
                        found_hint = m.get_arg_annotation(hint_lineno0, name)

                    init_hint_unparsed = ast.unparse(hint)
                    found_hint_unparsed = ast.unparse(found_hint)
                    assert found_hint_unparsed == init_hint_unparsed
