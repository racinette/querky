import typing
import gc
import sys
import types
from importlib.machinery import ModuleSpec
from contextlib import contextmanager
import inspect


def like_module(d: typing.Any) -> dict[str, typing.Any] | None:
    b = (
        isinstance(d, dict)
        and (modulename := d.get("__name__")) is not None
        and modulename != "__main__"
        and isinstance(d.get("__spec__"), ModuleSpec)
    )
    if b:
        return d
    return None


def like_class(d: typing.Any):
    b: bool = (
        isinstance(d, dict)
        and "__module__" in d
        and "__doc__" in d
        and "__annotations__" not in d
    )


def isstaticmethod(fn: types.FunctionType) -> bool:
    referrers = gc.get_referrers(fn)
    for ref in referrers:
        if isinstance(ref, staticmethod):
            return True
    return False


def isinstancemethod(obj: object):
    pass


def resolve_import2(obj: object):
    """
    It is important for the algorithm to know beforehand what it is looking for.

    """

    if inspect.ismethod(obj):
        # CLASS method or INSTANCE method
        if inspect.isclass(obj.__self__):
            # CLASS method
            # We're going to be looking for a CLASS,
            # which has defined this classmethod.
            pass
        else:
            # INSTANCE method
            # We're going to be looking for a module-level reference
            # to this particular object's method.
            pass
    elif inspect.isfunction(obj):
        # STATIC method or regular function
        if isstaticmethod(obj):
            # STATIC method
            # We're going to be looking for a class,
            # which has defined this staticmethod.
            pass
        else:
            # POF (Plain Old Function, aye)
            # We're gonna be looking for a module-level reference.
            pass
    elif inspect.isclass(obj):
        pass
    else:
        pass

    referrers = gc.get_referrers(obj)
    dict_referrers = [
        referrer for referrer in referrers if isinstance(referrer, dict)
    ]
    if not dict_referrers:
        raise ValueError(
            "Unable to resolve imports: no dictionaries refer to this object."
        )


def resolve_import(
    obj: object,
) -> list[tuple[types.ModuleType, str, tuple[str, ...]]]:
    referrers = gc.get_referrers(obj)
    module_dicts = [
        module
        for referrer in referrers
        if (module := like_module(referrer)) is not None
    ]
    module_names = {module_dict["__name__"] for module_dict in module_dicts}
    modules: list[tuple[types.ModuleType, tuple[str, ...], str]] = []
    for modulename, moduleobj in sys.modules.items():
        if modulename not in module_names:
            continue
        module_names.remove(modulename)
        varnames: list[str] = []
        protected_varnames: list[str] = []
        for varname, varval in moduleobj.__dict__.items():
            if varval is obj:
                if varname.startswith("_"):
                    protected_varnames.append(varname)
                else:
                    varnames.append(varname)
        if varnames:
            varname = varnames[0]
        elif protected_varnames:
            varname = protected_varnames[0]
        else:
            continue
        modules.append((moduleobj, (), varname))
    if not modules:
        pass
    return modules


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
    was_enabled = gc.isenabled()
    try:
        gc.collect()
        if was_enabled:
            gc.disable()
        yield
    finally:
        if was_enabled:
            gc.enable()
