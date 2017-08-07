import typing as typ
import itertools as it
import functools as ft

import taggu.exceptions as tex


class TooManyArgsException(tex.TagguException):
    pass


class NotEnoughArgsException(tex.TagguException):
    pass


class InvalidArgTypeException(tex.TagguException):
    pass


def validate_types(args: typ.Sequence,
                   types: typ.Iterable[typ.Union[typ.Type, typ.Sequence[typ.Type]]],
                   more_ok: bool) -> bool:
    """Validates a fixed-length collection of arguments against a (potentially infinite) iterable of
    types/tuples of types.
    """
    num_args = len(args)

    t_it = iter(types)
    types_coll = tuple(it.islice(t_it, num_args))

    if len(args) != len(types_coll):
        return False

    if not more_ok:
        for _ in t_it:
            return False

    for a, t in zip(args, types_coll):
        if not isinstance(a, t):
            return False

    return True


def normalize_arg_sequence(args: typ.Sequence, desired_len: int, def_vals: typ.Sequence=()) -> typ.Sequence:
    num_args = len(args)
    if num_args > desired_len:
        raise TooManyArgsException()

    if num_args == desired_len:
        return args

    if num_args + len(def_vals) < desired_len:
        raise NotEnoughArgsException()

    num_needed_defs = desired_len - num_args
    assert num_needed_defs > 0

    return tuple(it.chain(args, def_vals[-num_needed_defs:]))


def vt_deco_gen(types: typ.Iterable[typ.Union[typ.Type, typ.Sequence[typ.Type]]], more_ok: bool):
    def deco(func: typ.Callable) -> typ.Callable:
        def wrapped(*args: typ.Any) -> typ.Any:
            if not validate_types(args=args, types=types, more_ok=more_ok):
                raise InvalidArgTypeException()

            return func(*args)

        return wrapped

    return deco


def na_deco_gen(desired_len: int, def_vals: typ.Sequence=()):
    def deco(func: typ.Callable) -> typ.Callable:
        def wrapped(*args: typ.Any) -> typ.Any:
            args = normalize_arg_sequence(args=args, desired_len=desired_len, def_vals=def_vals)
            return func(*args)

        return wrapped

    return deco

########################################################################################################################
#   List manipulation
########################################################################################################################


@vt_deco_gen(types=it.repeat((int, str)), more_ok=True)
def list_(*args):
    return tuple(args)


@na_deco_gen(desired_len=3, def_vals=('parent', None))
@vt_deco_gen(types=(str, str, (str, type(None))), more_ok=False)
def lookup(*args):
    print(len(args))
    print(args)
