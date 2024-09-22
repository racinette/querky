def create_func(i: int):
    def some_func(i2: int):
        return i + i2

    return some_func


def create_type(s: str):
    class Foo:
        bar = s

    return Foo


def create_generic_func(t: type):
    def create_object(i) -> t | None:  # type: ignore
        return t(i)

    return create_object
