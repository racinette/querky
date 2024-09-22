import gc
import typing
import inspect
import types
import time
from contextlib import contextmanager

from pydantic import BaseModel

import tests.some1
import tests.some2
from tests.some3 import Boot, valenok, Foo
from tests.some_module2 import f1, f2, c1, g1


from tests.some0 import JSON

# from querky.import_resolver import resolve_import

from typing import Optional, Union


# s = time.time()
# g = referrers.get_referrer_graph(Foo.Bar.Skibidi.valenok2)
# e = time.time()
# print(g)
# print(e - s)

# a0 = gc.get_referrers(Foo.Bar.Skibidi.valenok2)


def get_variable_names(container, obj) -> list[str]:
    varnames: list[str] = []
    protected_varnames: list[str] = []
    for varname, varval in container.__dict__.items():
        if varval is obj:
            if varname.startswith("_"):
                protected_varnames.append(varname)
            else:
                varnames.append(varname)
    return [*varnames, *protected_varnames]


def get_unique_referrers(node, cache):
    i = id(node)
    try:
        return cache[i]
    except KeyError:
        result = gc.get_referrers(node)
        frame = inspect.currentframe()
        if frame is not None:
            locs = frame.f_locals
            result = tuple(elem for elem in result if elem is not locs)
        else:
            result = tuple(result)
        result = unique_objects(result)
        cache[i] = result
        return result


def unique_objects(vals):
    d = {id(val): val for val in vals}
    return tuple(d.values())


def remove_ids(vals, remove):
    return tuple(val for val in vals if id(val) not in remove)


def _climb_down_reference_tree(obj, hierarchy, circular, cache):
    if cache is None:
        cache = dict()
    if hierarchy is None:
        hierarchy = (obj,)
    if circular is None:
        circular = {id(obj), id(cache), id(hierarchy)}
    ways = []
    nodes = get_unique_referrers(obj, cache)
    nodes = remove_ids(nodes, circular)
    for node in nodes:
        if isinstance(node, dict):
            # maybe a class? a module?
            refs = get_unique_referrers(node, cache)
            refs = remove_ids(refs, circular)
            for ref in refs:
                if inspect.isclass(ref):
                    # classes have `mappingproxies` for __dict__,
                    # but we still get a regular `dict` from the gc,
                    # so we can only check for equality, and not for identity
                    d = ref.__dict__
                    if d == node:
                        new_hierarchy = (ref, *hierarchy)
                        results = _climb_down_reference_tree(
                            ref,
                            new_hierarchy,
                            {*circular, id(ref), id(node)},
                            cache,
                        )
                        ways.extend(results)
                        break
                elif inspect.ismodule(ref):
                    # it is a module! great!
                    if ref.__name__ == "__main__":
                        continue
                    d = ref.__dict__
                    if d is node:
                        curr = (ref, *hierarchy)
                        ways.append((curr, {*circular, id(ref), id(node)}))
        elif isinstance(node, staticmethod):
            # staticmethod exports reference to the original function,
            # but the class holds reference to the staticmethod instance
            ways.extend(
                _climb_down_reference_tree(
                    node, hierarchy, {*circular, id(node)}, cache
                )
            )

    if (self := getattr(obj, "__self__", None)) and inspect.ismethod(obj):
        # bound methods, class methods
        new_hierarchy = (self, obj)
        ways.extend(
            _climb_down_reference_tree(
                self, new_hierarchy, {*circular, id(self)}, cache
            )
        )

    return ways


def climb_down_reference_tree(obj):
    return _climb_down_reference_tree(obj, None, None, None)


@contextmanager
def nogc():
    try:
        gc.collect()
        gc.disable()
        yield
    finally:
        gc.enable()


with nogc():
    w = climb_down_reference_tree(JSON)
# results = [(way, get_variable_names(way, obj)) for way in w]

aa = gc.get_referrers(Boot.SLIPPER)
b = gc.get_referrers(a[0])
c = gc.get_referrers(valenok.some_meth)
d = gc.get_referrers(Boot.some_class_meth)
e = gc.get_referrers(Boot.some_static_meth)
