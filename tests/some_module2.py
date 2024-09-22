from tests.some_module import create_func, create_type, create_generic_func


f1 = create_func(1)
f2 = create_func(2)


c1 = create_type("cheecks")
c2 = create_type("sponge bob")


class A:
    def __init__(self, i):
        self.i = i


g1 = create_generic_func(A)
