from tests.some_module2 import f1


JSON = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None
