import typing as typ
import numbers as num

import taggu.helpers as th

TagguList = typ.Sequence[str]

########################################################################################################################
#   List manipulation
########################################################################################################################


def list_(*scalars: str) -> TagguList:
    return tuple(scalars)


def count(lst: TagguList) -> int:
    return len(lst)


def elem(lst: TagguList, index: int) -> typ.Any:
    try:
        return lst[index]
    except IndexError:
        return None


def sort_(lst: TagguList) -> TagguList:
    return tuple(sorted(lst))


def sortn(lst: TagguList) -> TagguList:
    try:
        return tuple(sorted(lst, key=int))
    except ValueError:
        return sort_(lst=lst)


def uniq(lst: TagguList) -> TagguList:
    return tuple(th.dedupe(lst))

########################################################################################################################
#   Metadata access
########################################################################################################################


def meta(field_name: str, label: typ.Optional[str]=None) -> TagguList:
    # TODO: Need a context containing the path to an item!
    pass


def metap(field_name: str, label: typ.Optional[str]=None, max_depth: typ.Optional[int]=None) -> TagguList:
    # TODO: Need a context containing the path to an item!
    pass


def metac(field_name: str, label: typ.Optional[str]=None, max_depth: typ.Optional[int]=None) -> TagguList:
    # TODO: Need a context containing the path to an item!
    pass

########################################################################################################################
#   Arithmetic
########################################################################################################################


def add(a: num.Real, b: num.Real) -> num.Real:
    return a + b


def sub(a: num.Real, b: num.Real) -> num.Real:
    return a - b


def mul(a: num.Real, b: num.Real) -> num.Real:
    return a * b


def div(a: num.Real, b: num.Real) -> num.Real:
    return a / b


def mod(a: num.Real, b: num.Real) -> num.Real:
    return a % b


def min_(a: num.Real, b: num.Real) -> num.Real:
    return min(a, b)


def max_(a: num.Real, b: num.Real) -> num.Real:
    return max(a, b)


def neg(a: num.Real) -> num.Real:
    return -a

########################################################################################################################
#   Logical comparisons
########################################################################################################################


def eq(a: num.Real, b: num.Real) -> bool:
    return a == b


def ne(a: num.Real, b: num.Real) -> bool:
    return a != b


def gt(a: num.Real, b: num.Real) -> bool:
    return a > b


def lt(a: num.Real, b: num.Real) -> bool:
    return a < b


def ge(a: num.Real, b: num.Real) -> bool:
    return a >= b


def le(a: num.Real, b: num.Real) -> bool:
    return a <= b

########################################################################################################################
#   Boolean operations
########################################################################################################################


def and_(*pred: bool) -> bool:
    return all(pred)


def or_(*pred: bool) -> bool:
    return any(pred)


def xor_(*pred: bool) -> bool:
    res = False
    for p in pred:
        res ^= p
    return res


def not_(pred: bool) -> bool:
    return not pred

########################################################################################################################
#   Control flow
########################################################################################################################

T = typ.TypeVar('T')
U = typ.TypeVar('U')


def if_(cond: bool, then_val: T) -> typ.Optional[T]:
    if cond:
        return then_val
    return None


def ifelse(cond: bool, then_val: T, else_val: U) -> typ.Union[T, U]:
    if cond:
        return then_val
    return else_val


def default(val: T, else_val: U) -> typ.Union[T, U]:
    if bool(val):
        return val
    return else_val


def first(*vals: T) -> typ.Optional[T]:
    for val in vals:
        if bool(val):
            return val

    return None


def guard(*vals: T) -> typ.Optional[str]:
    ret = None
    for val in vals:
        if bool(val):
            if ret is None:
                ret = ''
            ret += str(val)
        else:
            return None
    return ret

########################################################################################################################
#   String manipulation
########################################################################################################################


def length(string: str) -> int:
    return len(string)


def join(lst: TagguList, sep: str) -> str:
    return sep.join(lst)


def joinl(lst: TagguList, sep: str, last_sep: str) -> str:
    f_lst = lst[:-1]
    l_elem = lst[-1:]

    f_join = [sep.join(f_lst)]
    f_join.extend(l_elem)

    return last_sep.join(f_join)


def joinlt(lst: TagguList, sep: str, last_sep: str, two_sep: str) -> str:
    if len(lst) == 2:
        return two_sep.join(lst)

    return joinl(lst=lst, sep=sep, last_sep=last_sep)

########################################################################################################################
#   Variables
########################################################################################################################


def put(name: str, val: T) -> T:
    # TODO: Need a context containing instance variables!
    pass


def puts(name: str, val: T) -> None:
    # TODO: Need a context containing instance variables!
    pass


def get(name: str) -> typ.Optional[T]:
    # TODO: Need a context containing instance variables!
    pass

########################################################################################################################
#   Utility & helper methods
########################################################################################################################


def valid(val: T) -> bool:
    return bool(val)


def index() -> int:
    # TODO: Need a context containing the path to an item!
    pass


def total() -> int:
    # TODO: Need a context containing the path to an item!
    pass


def nil(*_: T) -> None:
    pass
