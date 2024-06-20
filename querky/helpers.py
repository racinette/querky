class ReprHelper:
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return self.name


class DictGetAttr:
    def __init__(self, d: dict) -> None:
        self.__d = d

    def __getattr__(self, item: str):
        return self.__d[item]


def to_camel_case(snake_str):
    return "".join(x.capitalize() for x in snake_str.lower().split("_"))


__all__ = ["ReprHelper", "DictGetAttr", "to_camel_case"]
