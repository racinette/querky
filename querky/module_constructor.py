from __future__ import annotations

import os
from os import path
import types
import typing

if typing.TYPE_CHECKING:
    from querky.querky import Querky


class ModuleConstructor:
    def __init__(
            self,
            querky: Querky,
            module: types.ModuleType,
            fullpath: str,
            module_path: str,
            filedir: str
    ):
        self.module = module
        self.querky = querky
        self.imports = set(querky.imports)
        self.exports = set()
        self.fullpath = fullpath
        self.module_path = module_path
        self.filedir = filedir

        self.queries_list = []

    def indent(self, i: int) -> str:
        return self.querky.get_indent(i)

    def _post_init(self):
        # Generate module code
        code = []
        for query in self.queries_list:
            query_code = query.generate_code()
            if not query_code:
                continue
            code.append('')
            code.append('')
            code.extend(query_code)
        code.append('')

        # Collect imports
        for query in self.queries_list:
            self.imports.update(query.get_imports())

        # Collect exports
        for query in self.queries_list:
            self.exports.update(query.get_exports())

        # Create import lines
        imports = [
            *getattr(self.module, '__imports__', []),
            *self.imports
        ]

        for query in self.queries_list:
            imports.append(
                f"from {self.module.__name__} import {query.query.__name__} as {query.local_name}"
            )

        # Imports + Code
        code = [
            *imports,
            *code,
        ]

        # If there are exports, create them at the end of the file (__all__)
        if self.exports:
            code.append('')
            code.append('__all__ = [')
            for export in self.exports:
                code.append(f'{self.indent(1)}"{export}",')
            code.append(']')
            code.append('')

        self.querky.sign_file_contents(code)

        code = '\n'.join(code)

        # checking, if file already exists
        file_exists = path.isfile(self.fullpath)
        if file_exists:
            # check, if we can overwrite the contents
            self.querky.check_file_is_mine(self.fullpath)

        if self.querky.subdir:
            os.makedirs(self.filedir, exist_ok=True)

        with open(self.fullpath, encoding='utf-8', mode='w') as f:
            f.write(code)

    async def generate_module(self, db):
        for query in self.queries_list:
            await query.fetch_types(db)
        self._post_init()

    def generate_module_sync(self, db):
        for query in self.queries_list:
            query.fetch_types_sync(db)
        self._post_init()
