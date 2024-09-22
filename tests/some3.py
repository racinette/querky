import typing

from tests.some_module2 import f1

from enum import StrEnum


class PlainOldPythonObject:
    def __init__(self, i):
        self.i = i

    def print(self):
        print(self.i)


def dummy_decorator(s):
    print("roflan")
    D["kekich"] = s
    s.valenok2 = s.valenok
    s.valenok = 1
    s.skibidi_mini = s()
    s.skibidi_maxi = s
    return s


def other_dec(meth):
    def gofuckyour(self, *args, **kwargs):
        print("lol")
        return meth(self, *args, **kwargs)

    return gofuckyour


class Boot(StrEnum):
    VALENOK = "valenok"
    SNEAKER = "sneaker"
    SLIPPER = "slipper"

    @other_dec
    def some_meth(self, val):
        pass

    @classmethod
    @other_dec
    def some_class_meth(cls, val):
        pass

    @staticmethod
    def some_static_meth(val):
        pass


def s(a: typing.Literal[Boot.SLIPPER, Boot.VALENOK]) -> str: ...


valenok = Boot.VALENOK


D = {}


def realdeal(fn):
    def deco():
        print("test")
        return fn()

    return deco


class Foo:
    class Bar:
        @dummy_decorator
        class Skibidi:
            valenok = valenok

            @staticmethod
            @realdeal
            @staticmethod
            @realdeal
            @staticmethod
            def whoa():
                print("bitch please")


a = {"B": valenok}


skibidi = PlainOldPythonObject(1)

ccc = Boot.some_static_meth
