import typing
from enum import StrEnum, auto
from random import Random


class State(StrEnum):
    MODULE = auto()
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    WITH = auto()
    TRY = auto()
    EXCEPT = auto()
    FINALLY = auto()
    DEF = auto()
    DECORATOR = auto()



ENTERNODES = {State.IF, State.WHILE, State.FOR, State.WITH, State.TRY, State.DECORATOR, State.DEF}
EXITNODES: dict[State, set[State]] = {
    State.MODULE: set(),
    State.IF: {State.ELIF, State.ELSE},
    State.ELIF: {State.ELIF, State.ELSE},
    State.ELSE: set(),
    State.WHILE: {State.ELSE},
    State.FOR: {State.ELSE},
    State.WITH: set(),
    State.TRY: {State.EXCEPT, State.FINALLY},
    State.EXCEPT: {State.ELSE, State.FINALLY},
    State.FINALLY: set(),
    State.DECORATOR: {State.DEF},
    State.DEF: set()
}


class ModuleGenerator:
    def __init__(
        self,
        indentation: str = " " * 4,
        modulename: str = "module",
        importname: str = "import",
        aliasname: str = "alias",
        random: Random | None = None,
    ) -> None:
        self.indentation = indentation
        self.current_indentation_level = 0
        self.state_stack = [State.MODULE]
        self.import_idx = 0
        self.import_idx = 0
        self.alias_idx = 0
        self.imported_names = set()
        self.modulename = modulename
        self.importname = importname
        self.aliasname = aliasname
        if random is None:
            random = Random(1234)
        self.random = random
        self.lines = []

    def indent(self):
        self.current_indentation_level += 1

    def dedent(self):
        self.current_indentation_level -= 1
        self.current_indentation_level = max(0, self.current_indentation_level)

    def i(self, add: int = 0):
        assert add >= 0
        return self.indentation * (self.current_indentation_level + add)

    @property
    def peek_state(self) -> State:
        return self.state_stack[-1]

    def if_statement(self, cond: str):
        pass

    def elif_statement(self, cond: str):
        pass

    def while_statement(self, cond: str):
        pass

    def for_statement(self, iter_clause: str):
        pass

    def with_statement(self, clause: str):
        pass

    def else_statement(self):
        pass

    def try_statement(self):
        pass

    def except_statement(self, exc: str):
        pass

    def finally_statement(self):
        pass

    def end_statement(self):
        pass

    def get_modulename(self):
        self.import_idx += 1
        return f"{self.modulename}{self.import_idx}"

    def get_aliasname(self):
        self.alias_idx += 1
        return f"{self.aliasname}{self.alias_idx}"

    def get_importname(self):
        self.import_idx += 1
        return f"{self.importname}{self.import_idx}"

    def get_modulechain(self):
        chain = [self.get_modulename()]
        while self.random.random() < 0.1:
            chain.append(self.get_modulename())
        modulename = ".".join(chain)
        return modulename

    def get_importnames(self):
        imports = [self.get_importname()]
        while self.random.random() < 0.3:
            imports.append(self.get_importname())
        return imports

    def get_aliased_importnames(self):
        importnames = self.get_importnames()
        imported_aliases = set()
        new_importnames = []
        for importname in importnames:
            alias = self.get_aliasname()
            name = f"{importname} as {alias}"
            imported_aliases.add(alias)
            new_importnames.append(name)
        return new_importnames, imported_aliases

    def make_import_from(self, modulename: str, importnames: list[str]):
        inline = bool(self.random.randint(0, 1))
        indent = "" if inline else self.i(1)
        div = ", " if inline else f",\n{indent}"
        s = indent + div.join(importnames)
        if not inline:
            s = f"(\n{s}\n{self.i()})"
        return f"from {modulename} import {s}"

    def import_statement(
        self,
        importtype: typing.Literal[
            "import",
            "import_as",
            "from_import",
            "from_import_as",
            "from_import_star",
        ],
    ) -> None:
        if importtype == "import":
            # import module1.module2.module3
            modulename = self.get_modulechain()
            self.imported_names.add(modulename)
            statement = f"import {modulename}"
        elif importtype == "import_as":
            # import module1.module2.module3 as alias1
            modulename = self.get_modulechain()
            alias = self.get_aliasname()
            self.imported_names.add(alias)
            statement = f"import {modulename} as {alias}"
        elif importtype == "from_import":
            # from module1.module2 import import1, import2
            modulename = self.get_modulechain()
            importnames = self.get_importnames()
            self.imported_names.update(importnames)
            statement = self.make_import_from(modulename, importnames)
        elif importtype == "from_imports_as":
            # from module1 import import1 as alias1, import2 as alias2
            modulename = self.get_modulechain()
            importnames, imported_aliases = self.get_aliased_importnames()
            self.imported_names.update(imported_aliases)
            statement = self.make_import_from(modulename, importnames)
        elif importtype == "from_import_star":
            # from module1.module2.module3 import *
            modulename = self.get_modulechain()
            statement = f"from {modulename} import *"
        else:
            raise NotImplementedError()

        statement = f"{self.i()}{statement}"
        self.lines.append(statement)

    def create(self):
        for _ in range(random.randint(0, 10)):
        t = random.random()
        if t < 0.3:
            importtype = "import"
        if t < 0.5:
            importtype = "import_as"
        elif t < 0.65:
            importtype = "from_import"
        elif t < 0.90:
            importtype = "from_import_as"
        else:
            importtype = "from_import_star"
        import_repr, _ = _generate_random_import(
            "module", "import", "alias", importtype
        )
        imports.append(import_repr)

